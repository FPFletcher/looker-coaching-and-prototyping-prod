import os
import requests

def run():
    print(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

if __name__ == "__main__":
    run()
