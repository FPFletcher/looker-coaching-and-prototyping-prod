import os
import requests
import urllib3
urllib3.disable_warnings()
from looker_sdk import init40

urls = [
    "https://8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app",
    "https://looker-core-demo-ffrancois.eu.looker.com",
    "https://looker-core-demo-ffrancois.europe-west1.looker.com",
    "https://mycompany.looker.com"
]

def format_url(url):
    is_looker_original = url.endswith(".com") and not url.endswith(".eu.looker.com") and not url.endswith(".europe-west1.looker.com")
    is_default_dummy = "8168ca92-acf6-485c-aba1-0dbf0987da05.looker.app" in url
    if (is_looker_original or is_default_dummy) and ":19999" not in url:
        return url + ":19999"
    return url

print("Testing Internal Parsing:")
for u in urls:
    print(f"Input: {u} -> Output: {format_url(u)}")

print("\nDeploying Backend...")
