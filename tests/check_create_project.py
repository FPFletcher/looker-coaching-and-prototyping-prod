import looker_sdk
from looker_sdk import methods40
import inspect

print("Checking for create_project method in Looker40SDK class...")
if hasattr(methods40.Looker40SDK, "create_project"):
    print("Found create_project method!")
    sig = inspect.signature(getattr(methods40.Looker40SDK, "create_project"))
    print(f"Signature: {sig}")
else:
    print("create_project method NOT found.")
    # Check for similar
    for m in dir(methods40.Looker40SDK):
        if "create_project" in m:
            print(f"Found similar: {m}")
