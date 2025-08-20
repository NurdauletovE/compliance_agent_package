#!/usr/bin/env python3
"""
Test script for the updated OpenSCAP agent functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import the agent
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent import OpenSCAPScanner

async def test_scanner():
    """Test the OpenSCAP scanner functionality"""
    print("Testing OpenSCAP Scanner...")
    
    # Initialize scanner with current directory paths
    scanner = OpenSCAPScanner(content_path="./content/")
    
    # Update the results directory to current directory
    scanner.results_dir = Path("./results")
    scanner.results_dir.mkdir(exist_ok=True)
    
    # Test the datastream detection
    print(f"Detected datastream: {scanner._detect_datastream()}")
    
    # Test scan with CIS Level 1 Server profile (same as we tested manually)
    profile = "xccdf_org.ssgproject.content_profile_cis_level1_server"
    print(f"Testing scan with profile: {profile}")
    
    try:
        results = await scanner.scan_system(profile)
        
        print("\n=== SCAN RESULTS ===")
        print(f"Scan ID: {results.get('scan_id')}")
        print(f"Profile: {results.get('profile')}")
        print(f"Datastream: {results.get('datastream')}")
        print(f"Status: {results.get('status', 'N/A')}")
        print(f"Exit Code: {results.get('exit_code', 'N/A')}")
        
        # Show stdout/stderr for debugging
        if results.get('stdout'):
            print(f"STDOUT (first 500 chars): {results['stdout'][:500]}...")
        if results.get('stderr'):
            print(f"STDERR (first 500 chars): {results['stderr'][:500]}...")
        
        if 'rules_total' in results:
            print(f"Total Rules: {results.get('rules_total', 0)}")
            print(f"Passed: {results.get('rules_passed', 0)}")
            print(f"Failed: {results.get('rules_failed', 0)}")
            print(f"Not Applicable: {results.get('rules_notapplicable', 0)}")
            print(f"Compliance Score: {results.get('compliance_score', 0.0):.2%}")
        
        # Check if files were created
        if 'scan_id' in results:
            scan_id = results['scan_id']
            results_file = Path(f"/app/results/results_{scan_id}.xml")
            report_file = Path(f"/app/results/report_{scan_id}.html")
            
            # Check in current directory results folder too
            local_results_dir = Path("results")
            local_results_file = local_results_dir / f"results_{scan_id}.xml"
            local_report_file = local_results_dir / f"report_{scan_id}.html"
            
            for file_path, name in [
                (results_file, "Results XML"),
                (report_file, "Report HTML"),
                (local_results_file, "Local Results XML"),
                (local_report_file, "Local Report HTML")
            ]:
                if file_path.exists():
                    print(f"{name}: {file_path} ({file_path.stat().st_size} bytes)")
        
        return True
        
    except Exception as e:
        print(f"Error during scan: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("OpenSCAP Agent Test")
    print("=" * 50)
    
    success = asyncio.run(test_scanner())
    
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
        sys.exit(1)
