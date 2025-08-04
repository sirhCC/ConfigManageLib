#!/usr/bin/env python3
"""
Test our simple YAML parser with lists.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from simple_yaml import SimpleYaml

# Test basic list parsing
yaml_content = """
app:
  name: "TestApp"
  
list_values:
  - item1
  - item2
  - item3

services:
  web:
    ports:
      - "80:80"
      - "443:443"
"""

print("Testing YAML content:")
print(yaml_content)
print("\nParsed result:")

result = SimpleYaml.safe_load(yaml_content)
print(result)

print(f"\nlist_values: {result.get('list_values')}")
print(f"services.web.ports should be: ['80:80', '443:443']")

# Let's see what we actually get for the nested ports
if 'services' in result and 'web' in result['services']:
    print(f"Actual services.web.ports: {result['services']['web'].get('ports')}")
