import json

try:
    with open('swagger.json', 'r') as f:
        spec = json.load(f)
        
    print(f"Host: {spec.get('host')}")
    print(f"BasePath: {spec.get('basePath')}")
    print(f"Schemes: {spec.get('schemes')}")
    
    paths = spec.get('paths', {})
    print(f"Found {len(paths)} paths.")
    
    login_paths = [p for p in paths if 'login' in p]
    print("Paths containing 'login':")
    for p in login_paths:
        print(f" - {p}")
        
    # Check specifically for /login
    if '/login' in paths:
        print("\nFound /login definition!")
        print(json.dumps(paths['/login'], indent=2))
        
except Exception as e:
    print(f"Error: {e}")
