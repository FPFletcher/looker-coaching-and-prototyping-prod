import looker_sdk
from looker_sdk import methods40

print("--- CREATE + PROJECT/FILE ---")
for m in dir(methods40.Looker40SDK):
    if "create" in m.lower() and ("project" in m.lower() or "file" in m.lower() or "lookml" in m.lower()):
        print(m)

print("\n--- DELETE + PROJECT/FILE ---")
for m in dir(methods40.Looker40SDK):
    if "delete" in m.lower() and ("project" in m.lower() or "file" in m.lower() or "lookml" in m.lower()):
        print(m)
