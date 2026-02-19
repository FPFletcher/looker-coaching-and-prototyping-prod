
import requests
import logging

logging.basicConfig(level=logging.INFO)

def test_manual_ddg():
    url = "https://html.duckduckgo.com/html/"
    data = {"q": "python programming"}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    
    try:
        print(f"Requesting {url}...")
        resp = requests.post(url, data=data, headers=headers, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Response length:", len(resp.text))
            if "python" in resp.text.lower():
                print("✅ Found 'python' in response")
            else:
                print("❌ 'python' NOT found in response (possible captcha/block)")
            
            # Print snippet
            print(resp.text[:500])
        else:
            print("❌ Request failed")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_manual_ddg()
