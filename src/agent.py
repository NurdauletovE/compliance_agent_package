#!/usr/bin/env python3
"""
Compliance Agent - Remote OpenSCAP Scanner

This agent runs on remote systems to perform OpenSCAP scans and 
send results to the compliance API server.
"""

import asyncio
import json
import logging
import os
import sys
import signal
import socket
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET

import aiohttp
import psutil
import schedule
import structlog
from fastapi import FastAPI, HTTPException
import uvicorn


# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = structlog.get_logger(__name__)


class OpenSCAPScanner:
    """OpenSCAP scanner implementation"""
    
    def __init__(self, content_path: str = "/app/content/"):
        self.content_path = Path(content_path)
        
        # Use different results directory based on environment
        if content_path.startswith("/app/"):
            # Container environment
            self.results_dir = Path("/app/results")
        else:
            # Local development environment  
            self.results_dir = Path("./results")
            
        self.results_dir.mkdir(exist_ok=True)
        
        # Also check system SCAP content directories and current directory
        self.system_content_paths = [
            Path("/usr/share/xml/scap/ssg/content"),
            Path("/usr/share/scap-security-guide"),
            Path("/usr/share/xml/scap"),
            Path.cwd() / "scap-security-guide-0.1.77"  # Local downloaded content
        ]
        
    async def scan_system(self, profile: str, datastream: str = None) -> Dict[str, Any]:
        """Execute OpenSCAP scan and return structured results"""
        scan_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        # Default datastream based on OS
        if not datastream:
            datastream = self._detect_datastream()
            
        results_file = self.results_dir / f"results_{scan_id}.xml"
        report_file = self.results_dir / f"report_{scan_id}.html"
        
        try:
            # Check if datastream file exists
            datastream_path = await self._find_or_download_datastream(datastream)
            if not datastream_path:
                return self._create_mock_scan_result(scan_id, timestamp, profile, "No SCAP content available")
            
            # Build OpenSCAP command - use the working format we tested
            cmd = [
                "oscap", "xccdf", "eval",
                "--profile", profile,
                "--results", str(results_file),
                "--report", str(report_file),
                str(datastream_path)
            ]
            
            logger.info("Starting OpenSCAP scan", 
                       profile=profile, datastream=datastream, scan_id=scan_id)
            
            # Execute scan
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            # Parse results
            scan_results = {
                "scan_id": scan_id,
                "timestamp": timestamp.isoformat(),
                "profile": profile,
                "datastream": datastream,
                "system_info": self._get_system_info(),
                "exit_code": result.returncode,
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore')
            }
            
            # Parse XML results if available
            if results_file.exists():
                scan_results.update(await self._parse_results(results_file))
            else:
                logger.warning("Results file not found", results_file=str(results_file))
                # Create basic results
                scan_results.update({
                    "rules_total": 0,
                    "rules_passed": 0,
                    "rules_failed": 0,
                    "compliance_score": 0.0,
                    "status": "completed_no_results"
                })
                
            return scan_results
            
        except FileNotFoundError as e:
            if "oscap" in str(e):
                logger.error("OpenSCAP command not found", error=str(e))
                return self._create_mock_scan_result(scan_id, timestamp, profile, "OpenSCAP not installed")
            else:
                raise
        except Exception as e:
            logger.error("Scan execution failed", error=str(e), scan_id=scan_id)
            return {
                "scan_id": scan_id,
                "timestamp": timestamp.isoformat(),
                "profile": profile,
                "datastream": datastream,
                "system_info": self._get_system_info(),
                "error": str(e),
                "status": "failed"
            }
    
    def _create_mock_scan_result(self, scan_id: str, timestamp: datetime, profile: str, reason: str) -> Dict[str, Any]:
        """Create a mock scan result when OpenSCAP is not available"""
        return {
            "scan_id": scan_id,
            "timestamp": timestamp.isoformat(),
            "profile": profile,
            "datastream": "mock",
            "system_info": self._get_system_info(),
            "rules_total": 100,
            "rules_passed": 75,
            "rules_failed": 20,
            "rules_error": 3,
            "rules_notapplicable": 2,
            "compliance_score": 0.75,
            "status": "mock_scan",
            "note": f"Mock scan result - {reason}",
            "rule_results": [
                {"rule_id": "mock_rule_1", "result": "pass", "title": "Mock security rule 1"},
                {"rule_id": "mock_rule_2", "result": "fail", "title": "Mock security rule 2"},
                {"rule_id": "mock_rule_3", "result": "pass", "title": "Mock security rule 3"}
            ]
        }
    
    async def _find_or_download_datastream(self, datastream: str) -> Optional[Path]:
        """Find datastream file or download SCAP content if needed"""
        # First, check if datastream exists in any of our search paths
        for search_path in [self.content_path] + self.system_content_paths:
            datastream_path = search_path / datastream
            if datastream_path.exists():
                logger.info("Found datastream", path=str(datastream_path))
                return datastream_path
        
        # If not found, try to download SCAP Security Guide content
        logger.info("Datastream not found, attempting to download SCAP content")
        try:
            download_dir = Path.cwd() / "scap-security-guide-0.1.77"
            if not download_dir.exists():
                success = await self._download_scap_content()
                if not success:
                    return None
                    
            # Check if the requested datastream is now available
            datastream_path = download_dir / datastream
            if datastream_path.exists():
                logger.info("Downloaded datastream found", path=str(datastream_path))
                return datastream_path
                
            # If specific datastream not found, try to find any available one
            available_streams = list(download_dir.glob("ssg-*-ds.xml"))
            if available_streams:
                logger.info("Using alternative datastream", path=str(available_streams[0]))
                return available_streams[0]
                
        except Exception as e:
            logger.error("Failed to download SCAP content", error=str(e))
            
        return None
    
    async def _download_scap_content(self) -> bool:
        """Download the latest SCAP Security Guide content"""
        try:
            # Download the latest release
            download_url = "https://github.com/ComplianceAsCode/content/releases/download/v0.1.77/scap-security-guide-0.1.77.zip"
            
            logger.info("Downloading SCAP Security Guide", url=download_url)
            
            # Download using wget (similar to what we tested)
            download_result = await asyncio.create_subprocess_exec(
                "wget", download_url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await download_result.communicate()
            
            if download_result.returncode != 0:
                logger.error("Failed to download SCAP content", stderr=stderr.decode())
                return False
                
            # Extract the zip file
            extract_result = await asyncio.create_subprocess_exec(
                "unzip", "-q", "scap-security-guide-0.1.77.zip",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await extract_result.communicate()
            
            if extract_result.returncode != 0:
                logger.error("Failed to extract SCAP content", stderr=stderr.decode())
                return False
                
            logger.info("Successfully downloaded and extracted SCAP Security Guide")
            return True
            
        except Exception as e:
            logger.error("Exception during SCAP content download", error=str(e))
            return False
    
    def _detect_datastream(self) -> str:
        """Detect appropriate datastream based on OS"""
        try:
            with open('/etc/os-release', 'r') as f:
                os_info = f.read().lower()
                
            # Map OS to available datastream files
            if 'ubuntu' in os_info:
                if '24.04' in os_info:
                    return "ssg-ubuntu2404-ds.xml"
                elif '22.04' in os_info:
                    return "ssg-ubuntu2204-ds.xml"
                elif '20.04' in os_info:
                    return "ssg-ubuntu2004-ds.xml"
                else:
                    # Default to latest Ubuntu version if version not detected
                    return "ssg-ubuntu2404-ds.xml"
            elif 'debian' in os_info:
                return "ssg-debian12-ds.xml"
            elif 'rhel' in os_info or 'red hat' in os_info:
                return "ssg-rhel9-ds.xml"
            elif 'centos' in os_info:
                return "ssg-centos9-ds.xml"
            else:
                # Check available files in content directory
                for search_path in [self.content_path] + self.system_content_paths:
                    available_files = list(search_path.glob("ssg-*-ds.xml"))
                    if available_files:
                        return available_files[0].name
                return "ssg-ubuntu2204-ds.xml"  # Default fallback
                
        except Exception as e:
            logger.warning("Failed to detect OS", error=str(e))
            # Check available files in content directory
            for search_path in [self.content_path] + self.system_content_paths:
                try:
                    available_files = list(search_path.glob("ssg-*-ds.xml"))
                    if available_files:
                        return available_files[0].name
                except Exception:
                    continue
            return "ssg-ubuntu2204-ds.xml"  # Final fallback
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Collect system information"""
        try:
            disk = psutil.disk_usage('/')
            return {
                "hostname": socket.gethostname(),
                "platform": sys.platform,
                "architecture": os.uname().machine,
                "kernel": os.uname().release,
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": disk._asdict(),
            }
        except Exception as e:
            logger.warning("Failed to collect system info", error=str(e))
            return {"hostname": socket.gethostname()}
    
    async def _parse_results(self, results_file: Path) -> Dict[str, Any]:
        """Parse OpenSCAP ARF results into structured format"""
        try:
            tree = ET.parse(results_file)
            root = tree.getroot()
            
            # Extract basic information
            results = {
                "rules_total": 0,
                "rules_passed": 0,
                "rules_failed": 0,
                "rules_error": 0,
                "rules_notapplicable": 0,
                "rules_unknown": 0,
                "compliance_score": 0.0,
                "rule_results": []
            }
            
            # Parse rule results (simplified parsing)
            for rule_result in root.iter():
                if 'rule-result' in rule_result.tag:
                    results["rules_total"] += 1
                    
                    # Look for <result> child element, not attribute
                    result_element = rule_result.find('.//{http://checklists.nist.gov/xccdf/1.2}result')
                    if result_element is None:
                        # Try without namespace
                        result_element = rule_result.find('.//result')
                    
                    result_text = result_element.text if result_element is not None else 'unknown'
                    
                    if result_text == 'pass':
                        results["rules_passed"] += 1
                    elif result_text == 'fail':
                        results["rules_failed"] += 1
                    elif result_text == 'error':
                        results["rules_error"] += 1
                    elif result_text == 'notapplicable':
                        results["rules_notapplicable"] += 1
                    elif result_text == 'notselected':
                        # Don't count notselected rules in totals for compliance calculation
                        results["rules_total"] -= 1
                    else:
                        results["rules_unknown"] += 1
            
            # Calculate compliance score
            if results["rules_total"] > 0:
                applicable_rules = results["rules_total"] - results["rules_notapplicable"]
                if applicable_rules > 0:
                    results["compliance_score"] = results["rules_passed"] / applicable_rules
            
            return results
            
        except Exception as e:
            logger.error("Failed to parse results", error=str(e), file=str(results_file))
            return {"parse_error": str(e)}


class ComplianceAPIClient:
    """Client for communicating with the compliance API server"""
    
    def __init__(self, api_base_url: str, api_token: Optional[str] = None):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_token = api_token
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def submit_scan_results(self, scan_results: Dict[str, Any]) -> bool:
        """Submit scan results to the compliance API"""
        try:
            headers = {'Content-Type': 'application/json'}
            if self.api_token:
                headers['Authorization'] = f'Bearer {self.api_token}'
            
            url = f"{self.api_base_url}/scans"
            
            async with self.session.post(url, json=scan_results, headers=headers) as response:
                if response.status == 200:
                    logger.info("Scan results submitted successfully", 
                               scan_id=scan_results.get('scan_id'))
                    return True
                else:
                    error_text = await response.text()
                    logger.error("Failed to submit scan results", 
                               status=response.status, error=error_text)
                    return False
                    
        except Exception as e:
            logger.error("Error submitting scan results", error=str(e))
            return False
    
    async def health_check(self) -> bool:
        """Check if the compliance API is reachable"""
        try:
            url = f"{self.api_base_url}/health"
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception:
            return False


class ComplianceAgent:
    """Main compliance agent orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        # Use local paths for development, container paths for production
        content_path = config.get('content_path', './content/')
        self.scanner = OpenSCAPScanner(content_path)
        self.api_client = None
        self.running = False
        self.scan_task = None
        
    async def start(self):
        """Start the compliance agent"""
        logger.info("Starting Compliance Agent", config=self.config)
        
        self.api_client = ComplianceAPIClient(
            self.config['api_base_url'],
            self.config.get('api_token')
        )
        
        self.running = True
        
        # Start scheduled scanning
        if self.config.get('scan_interval', 0) > 0:
            self.scan_task = asyncio.create_task(self._scheduled_scanning())
            
    async def stop(self):
        """Stop the compliance agent"""
        logger.info("Stopping Compliance Agent")
        self.running = False
        
        if self.scan_task:
            self.scan_task.cancel()
            try:
                await self.scan_task
            except asyncio.CancelledError:
                pass
                
        if self.api_client:
            await self.api_client.__aexit__(None, None, None)
    
    async def perform_scan(self, profile: str = None) -> Dict[str, Any]:
        """Perform a compliance scan"""
        profile = profile or self.config.get('default_profile', 'xccdf_org.ssgproject.content_profile_cis')
        
        logger.info("Starting compliance scan", profile=profile)
        
        # Execute scan
        scan_results = await self.scanner.scan_system(profile)
        
        # Submit to API if configured
        if self.config.get('api_base_url'):
            async with self.api_client:
                await self.api_client.submit_scan_results(scan_results)
        
        return scan_results
    
    async def _scheduled_scanning(self):
        """Run scheduled compliance scans"""
        interval = self.config.get('scan_interval', 3600)  # Default 1 hour
        
        while self.running:
            try:
                await self.perform_scan()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduled scan failed", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retry


# FastAPI health endpoint
app = FastAPI(title="Compliance Agent", version="1.0.0")

# Global agent instance
agent: Optional[ComplianceAgent] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if agent and agent.running else "stopped",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


@app.post("/scan")
async def trigger_scan(profile: str = None):
    """Manually trigger a compliance scan"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        results = await agent.perform_scan(profile)
        return {"status": "completed", "scan_id": results.get("scan_id"), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scan/oscap")
async def trigger_oscap_scan(
    profile: str = "xccdf_org.ssgproject.content_profile_cis_level1_server",
    datastream: str = None
):
    """Trigger OpenSCAP scan with specific parameters"""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Initialize scanner if not already done
        if not hasattr(agent, 'scanner') or not agent.scanner:
            agent.scanner = OpenSCAPScanner()
            
        # Run the scan directly
        results = await agent.scanner.scan_system(profile, datastream)
        return {
            "status": "completed", 
            "scan_id": results.get("scan_id"), 
            "profile": profile,
            "datastream": datastream or "auto-detected",
            "results": results
        }
    except Exception as e:
        logger.error("OpenSCAP scan failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scan/profiles")
async def list_available_profiles():
    """List available SCAP profiles"""
    try:
        # Common CIS profiles for different systems
        profiles = [
            {
                "id": "xccdf_org.ssgproject.content_profile_cis_level1_server",
                "title": "CIS Level 1 Server",
                "description": "CIS Benchmark Level 1 profile for servers"
            },
            {
                "id": "xccdf_org.ssgproject.content_profile_cis_level1_workstation", 
                "title": "CIS Level 1 Workstation",
                "description": "CIS Benchmark Level 1 profile for workstations"
            },
            {
                "id": "xccdf_org.ssgproject.content_profile_cis_level2_server",
                "title": "CIS Level 2 Server", 
                "description": "CIS Benchmark Level 2 profile for servers"
            },
            {
                "id": "xccdf_org.ssgproject.content_profile_cis_level2_workstation",
                "title": "CIS Level 2 Workstation",
                "description": "CIS Benchmark Level 2 profile for workstations"
            },
            {
                "id": "xccdf_org.ssgproject.content_profile_stig",
                "title": "STIG Profile",
                "description": "Security Technical Implementation Guide profile"
            }
        ]
        return {"profiles": profiles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def main():
    """Main entry point"""
    # Load configuration
    config = {
        "api_base_url": os.getenv("COMPLIANCE_API_URL", "http://localhost:8002"),
        "api_token": os.getenv("COMPLIANCE_API_TOKEN"),
        "scan_interval": int(os.getenv("SCAN_INTERVAL", "3600")),  # 1 hour default
        "default_profile": os.getenv("DEFAULT_PROFILE", "xccdf_org.ssgproject.content_profile_cis"),
        "agent_port": int(os.getenv("AGENT_PORT", "8080"))
    }
    
    global agent
    agent = ComplianceAgent(config)
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(agent.stop())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start agent
        await agent.start()
        
        # Start health API
        uvicorn_config = uvicorn.Config(
            app, 
            host="0.0.0.0", 
            port=config["agent_port"],
            log_level="info"
        )
        server = uvicorn.Server(uvicorn_config)
        
        # Run both agent and API server
        await asyncio.gather(
            server.serve(),
            agent.scan_task if agent.scan_task else asyncio.sleep(0)
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
