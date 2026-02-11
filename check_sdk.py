import looker_sdk
from looker_sdk import methods40
import inspect

# Print methods related to requested tools
print("--- PROJECT METHODS ---")
for m in dir(methods40.Looker40SDK):
    if "project" in m.lower():
        print(m)

print("\n--- CONNECTION METHODS ---")
for m in dir(methods40.Looker40SDK):
    if "connection" in m.lower():
        print(m)

print("\n--- HEALTH/VALIDATION METHODS ---")
for m in dir(methods40.Looker40SDK):
    if "validate" in m.lower() or "usage" in m.lower() or "monitor" in m.lower():
        print(m)
