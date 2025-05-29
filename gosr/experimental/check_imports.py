# check_imports.py
with open("imported_modules.txt") as f:
    modules = [line.strip() for line in f if line.strip()]

import importlib

missing = []
for mod in modules:
    try:
        importlib.import_module(mod)
    except ImportError:
        missing.append(mod)

if missing:
    print("Missing modules in your environment:")
    for m in missing:
        print(m)
else:
    print("All imported modules are available in your environment.")