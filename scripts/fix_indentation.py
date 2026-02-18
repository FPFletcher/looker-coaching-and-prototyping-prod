import os

files_to_fix = [
    'apps/agent/field_fetching_methods.py',
    'apps/agent/lookml_context_methods.py',
    'apps/agent/lookml_registration_helper.py',
    'apps/agent/register_lookml_manually_method.py'
]

def clean_file(path):
    if not os.path.exists(path):
        print(f"Skipping {path} (not found)")
        return
    with open(path, 'r') as f:
        lines = f.readlines()
    
    # SYSTEMATIC FIX: Convert all tabs to 4 spaces and rstrip trailing whitespace
    cleaned = [line.replace('\t', '    ').rstrip() + '\n' for line in lines]
    
    with open(path, 'w') as f:
        f.writelines(cleaned)
    print(f"✅ Cleaned and normalized: {path}")

for f in files_to_fix:
    clean_file(f)
