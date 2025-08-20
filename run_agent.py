#!/usr/bin/env python3
"""
Test runner for the OpenSCAP compliance agent
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    # Set environment variables for testing
    os.environ.setdefault("COMPLIANCE_API_URL", "http://localhost:8002")
    os.environ.setdefault("SCAN_INTERVAL", "0")  # Disable scheduled scanning for testing
    os.environ.setdefault("DEFAULT_PROFILE", "xccdf_org.ssgproject.content_profile_cis_level1_server")
    os.environ.setdefault("AGENT_PORT", "8081")
    
    # Import and run the agent
    from agent import main
    import asyncio
    
    print("Starting OpenSCAP Compliance Agent for testing...")
    print("API will be available at: http://localhost:8081")
    print("Available endpoints:")
    print("  GET  /health - Health check")
    print("  GET  /scan/profiles - List available profiles")
    print("  POST /scan/oscap - Trigger OpenSCAP scan")
    print()
    
    try:
        # Override the main function to add content_path config
        async def run_agent():
            import agent
            
            config = {
                "api_base_url": os.getenv("COMPLIANCE_API_URL", "http://localhost:8002"),
                "api_token": os.getenv("COMPLIANCE_API_TOKEN"),
                "scan_interval": int(os.getenv("SCAN_INTERVAL", "0")),
                "default_profile": os.getenv("DEFAULT_PROFILE", "xccdf_org.ssgproject.content_profile_cis_level1_server"),
                "agent_port": int(os.getenv("AGENT_PORT", "8080")),
                "content_path": "./content/"  # Use local content path
            }
            
            agent.agent = agent.ComplianceAgent(config)
            await agent.agent.start()
            
            # Start health API
            import uvicorn
            uvicorn_config = uvicorn.Config(
                agent.app, 
                host="0.0.0.0", 
                port=config["agent_port"],
                log_level="info"
            )
            server = uvicorn.Server(uvicorn_config)
            
            # Run server
            await server.serve()
        
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        print("\nShutting down agent...")
