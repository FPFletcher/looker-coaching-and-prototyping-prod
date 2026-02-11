import looker_sdk
from looker_sdk import methods40

print("--- HTTP METHODS ---")
# Check if there are raw HTTP methods on the SDK instance or transport
# We need to instantiate it to check instance methods sometimes (though dir() on class usually works for methods)
sdk = looker_sdk.init40()
for m in dir(sdk):
    if m in ['get', 'post', 'put', 'delete', 'patch']:
        print(f"SDK has method: {m}")
        
if hasattr(sdk, 'auth'):
    print("SDK has auth")
if hasattr(sdk, 'transport'):
    print("SDK has transport") 
