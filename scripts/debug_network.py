
import requests
import sys

def test_url(url):
    print(f"Testing {url}...")
    try:
        response = requests.get(url, timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Headers: {list(response.headers.keys())}")
        print(f"  Content (first 100 chars): {response.text[:100]}")
    except Exception as e:
        print(f"  FAILED: {e}")

if __name__ == "__main__":
    print("Python Requests Version:", requests.__version__)
    test_url("https://example.com")
    test_url("https://www.google.com")
    test_url("https://www.looker.com")
