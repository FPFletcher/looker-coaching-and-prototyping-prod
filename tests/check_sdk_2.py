import looker_sdk
from looker_sdk import methods40

print("--- FILE METHODS ---")
for m in dir(methods40.Looker40SDK):
    if "file" in m.lower():
        print(m)

print("\n--- DELETE METHODS ---")
for m in dir(methods40.Looker40SDK):
    if "delete" in m.lower():
        print(m)
