import urllib.request
import time

def check():
    start = time.time()
    try:
        req = urllib.request.Request("https://www.googleapis.com/oauth2/v3/certs")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read()
            print(f"Success in {time.time() - start:.2f}s: {len(data)} bytes")
    except Exception as e:
        print(f"Failed in {time.time() - start:.2f}s: {e}")

if __name__ == "__main__":
    check()
