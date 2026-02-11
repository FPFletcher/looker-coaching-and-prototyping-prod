
import requests
import os

def check():
    url = "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app/api/4.0/login"
    client_id = "vQyY8tbjsT6tcG7ZV85N"
    client_secret = "hyPbyWkJXDz8h6tGcYk5Y44G"
    
    print(f"POST {url}")
    print(f"ID: {client_id}")
    print(f"Secret: {client_secret[:4]}...{client_secret[-4:]}")
    
    data = {"client_id": client_id, "client_secret": client_secret}
    
    try:
        res = requests.post(url, data=data, verify=False) # Force verification off for debugging
        print(f"Status: {res.status_code}")
        print(f"Headers: {res.headers}")
        print(f"Body: {res.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
