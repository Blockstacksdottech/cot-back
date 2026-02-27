import requests
import time
import random
import sys
import os
from urllib.parse import quote

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from datahandler.utils import get_proxies
    from curl_cffi import requests as curl_requests
except ImportError:
    print("❌ Critical imports failed. Ensure you are running this from the project root and dependencies are installed.")
    sys.exit(1)

def test_proxy():
    print("🔍 Starting Comprehensive Proxy Test...\n")

    # 1. Test Direct Connection
    try:
        direct_ip = requests.get("https://api.ipify.org", timeout=10).text
        print(f"🏠 Direct IP (No Proxy): {direct_ip}")
    except Exception as e:
        print(f"⚠️ Could not fetch direct IP: {e}")

    # 2. Test Basic Proxy Masking
    print("\n--- Testing Basic Proxy Connection ---")
    proxies = get_proxies()
    if not proxies:
        print("❌ Proxy configuration not found in .env!")
        return

    try:
        proxy_ip = requests.get("https://api.ipify.org", proxies=proxies, timeout=30).text
        print(f"🌐 Proxy IP: {proxy_ip}")
        if proxy_ip != direct_ip:
            print("✅ SUCCESS: Proxy is correctly masking your home IP.")
        else:
            print("❌ FAILURE: Proxy IP is the same as your home IP!")
    except Exception as e:
        print(f"❌ Basic Proxy Failed: {e}")

    # 3. Test Sticky Sessions (IPRoyal Feature)
    print("\n--- Testing Sticky Sessions (IP Rotation) ---")
    session1_id = "test_abc123"
    session2_id = "test_xyz789"
    
    try:
        # Request 1 with Session A
        proxies1 = get_proxies(session_id=session1_id)
        ip1_a = requests.get("https://api.ipify.org", proxies=proxies1, timeout=30).text
        print(f"📍 Session A (Req 1): {ip1_a}")
        
        # Request 2 with Session A (Should be SAME)
        ip1_b = requests.get("https://api.ipify.org", proxies=proxies1, timeout=30).text
        print(f"📍 Session A (Req 2): {ip1_b}")
        
        # Request 3 with Session B (Should be DIFFERENT)
        proxies2 = get_proxies(session_id=session2_id)
        ip2 = requests.get("https://api.ipify.org", proxies=proxies2, timeout=30).text
        print(f"📍 Session B (Req 1): {ip2}")
        
        if ip1_a == ip1_b:
            print("✅ SUCCESS: Sticky sessions are holding the IP constant.")
        else:
            print("⚠️ WARNING: Sticky session did not hold the same IP.")
            
        if ip1_a != ip2:
            print("✅ SUCCESS: Different session IDs result in different IPs.")
        else:
            print("⚠️ WARNING: Different sessions got the same IP (this can happen occasionally with large pools).")
    except Exception as e:
        print(f"❌ Sticky Session Test Failed: {e}")

    # 4. Test Connectivity to Target APIs via curl_cffi
    print("\n--- Testing Target API Connectivity (with curl_cffi) ---")
    
    # Define targets with their specific requirements
    targets = [
        {
            "name": "Yahoo Finance (Chart API)",
            "url": "https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X",
            "method": "GET"
        },
        {
            "name": "MyFXBook Calendar (Search)",
            "url": "https://widget.myfxbook.com/calendar/search.html",
            "method": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://www.myfxbook.com/",
                "Origin": "https://www.myfxbook.com",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site"
            },
            "json": {
                "startDate": "2024-02-27T00:00:00.000Z",
                "endDate": "2024-02-27T23:59:59.999Z",
                "language": "en",
                "impacts": ["3", "2", "1", "0"],
                "currencies": ["USD"]
            }
        },
        {
            "name": "MyFXBook Community Outlook",
            "url": "https://www.myfxbook.com/community/outlook",
            "method": "GET",
            "headers": {
                "Referer": "https://www.myfxbook.com/",
                "Upgrade-Insecure-Requests": "1"
            }
        }
    ]

    for target in targets:
        name = target["name"]
        url = target["url"]
        method = target["method"]
        headers = target.get("headers", {})
        
        try:
            session_id = f"test_{random.randint(1000, 9999)}"
            proxies = get_proxies(session_id=session_id)
            
            print(f"🔗 Testing {name} ({method})...")
            
            if method == "POST":
                resp = curl_requests.post(
                    url, 
                    json=target.get("json"), 
                    headers=headers,
                    proxies=proxies, 
                    impersonate="chrome", 
                    timeout=30
                )
            else:
                resp = curl_requests.get(
                    url, 
                    headers=headers,
                    proxies=proxies, 
                    impersonate="chrome", 
                    timeout=30
                )
            
            if resp.status_code == 200:
                print(f"✅ {name} SUCCESS: 200 OK")
            else:
                print(f"❌ {name} FAILED: {resp.status_code}")
                if resp.status_code == 405:
                    print("   (Note: 405 often means GET was used on a POST-only endpoint)")
        except Exception as e:
            print(f"❌ {name} ERROR: {e}")

    print("\n🚀 Proxy test complete.")

if __name__ == "__main__":
    test_proxy()
