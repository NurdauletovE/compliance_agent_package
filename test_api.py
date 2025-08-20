#!/usr/bin/env python3
"""
Test the OpenSCAP agent API endpoints
"""

import asyncio
import aiohttp
import json

async def test_api_endpoints():
    """Test the OpenSCAP agent API endpoints"""
    base_url = "http://localhost:8081"
    
    print("Testing OpenSCAP Agent API Endpoints")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        print("1. Testing health endpoint...")
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check: {data}")
                else:
                    print(f"❌ Health check failed: {response.status}")
        except Exception as e:
            print(f"❌ Health check error: {e}")
        
        # Test profiles endpoint
        print("\n2. Testing profiles endpoint...")
        try:
            async with session.get(f"{base_url}/scan/profiles") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Available profiles:")
                    for profile in data['profiles']:
                        print(f"   - {profile['title']}: {profile['id']}")
                else:
                    print(f"❌ Profiles endpoint failed: {response.status}")
        except Exception as e:
            print(f"❌ Profiles endpoint error: {e}")
        
        # Test OpenSCAP scan endpoint
        print("\n3. Testing OpenSCAP scan endpoint...")
        try:
            scan_data = {
                "profile": "xccdf_org.ssgproject.content_profile_cis_level1_server"
            }
            
            print(f"   Starting scan with profile: {scan_data['profile']}")
            async with session.post(f"{base_url}/scan/oscap", 
                                   params=scan_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Scan completed:")
                    print(f"   Scan ID: {data['scan_id']}")
                    print(f"   Profile: {data['profile']}")
                    print(f"   Status: {data['status']}")
                    
                    results = data.get('results', {})
                    if 'rules_total' in results:
                        print(f"   Total Rules: {results.get('rules_total', 0)}")
                        print(f"   Passed: {results.get('rules_passed', 0)}")
                        print(f"   Failed: {results.get('rules_failed', 0)}")
                        print(f"   Compliance: {results.get('compliance_score', 0.0):.2%}")
                else:
                    text = await response.text()
                    print(f"❌ OpenSCAP scan failed: {response.status} - {text}")
        except Exception as e:
            print(f"❌ OpenSCAP scan error: {e}")

if __name__ == "__main__":
    print("Starting API endpoint tests...")
    print("Make sure the agent is running with: python src/agent.py")
    print()
    
    asyncio.run(test_api_endpoints())
