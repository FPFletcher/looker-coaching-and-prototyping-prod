import requests
import json

BASE = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app"
CID = "vQyY8tbjsT6tcG7ZV85N"
SEC = "hyPbyWkJXDz8h6tGcYk5Y44G"

def try_login(description, url, params=None, data=None, headers=None):
    print(f"--- {description} ---")
    print(f"POST {url}")
    try:
        resp = requests.post(url, params=params, data=data, headers=headers, timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

def main():
    # 1. Standard Form Data
    try_login("Standard /api/4.0/login (Form Data)", 
              f"{BASE}/api/4.0/login", 
              data={"client_id": CID, "client_secret": SEC})

    # 2. Query Params
    try_login("Query Params /api/4.0/login", 
              f"{BASE}/api/4.0/login", 
              params={"client_id": CID, "client_secret": SEC})

    # 3. JSON Body
    try_login("JSON Body /api/4.0/login", 
              f"{BASE}/api/4.0/login", 
              data=json.dumps({"client_id": CID, "client_secret": SEC}),
              headers={"Content-Type": "application/json"})

    # 4. Old API /api/3.1/login
    try_login("Old API /api/3.1/login", 
              f"{BASE}/api/3.1/login", 
              data={"client_id": CID, "client_secret": SEC})

    # 5. Root Login /login
    try_login("Root /login", 
              f"{BASE}/login", 
              data={"client_id": CID, "client_secret": SEC})

    # 6. API Root /api/login
    try_login("API Root /api/login", 
              f"{BASE}/api/login", 
              data={"client_id": CID, "client_secret": SEC})

    # 7. With port 19999 (if reachable)
    try_login("Port 19999 /api/4.0/login", 
              f"{BASE}:19999/api/4.0/login", 
              data={"client_id": CID, "client_secret": SEC})

if __name__ == "__main__":
    main()
