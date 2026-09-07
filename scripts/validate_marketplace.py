#!/usr/bin/env python3
import json
import os
import sys
import yaml

def main():
    if not os.path.exists("marketplace.json"):
        print("ERROR: marketplace.json not found")
        sys.exit(1)
        
    with open("marketplace.json") as f:
        try:
            manifest = json.load(f)
        except json.JSONDecodeError:
            print("ERROR: marketplace.json is not valid JSON")
            sys.exit(1)
            
    skills = manifest.get("skills", [])
    entrypoints = 0
    ids = set()
    
    for s in skills:
        sid = s.get("id")
        path = s.get("path")
        is_entry = s.get("entrypoint", False)
        
        if sid in ids:
            print(f"ERROR: Duplicate skill id: {sid}")
            sys.exit(1)
        ids.add(sid)
        
        if is_entry:
            entrypoints += 1
            
        if not os.path.exists(path):
            print(f"ERROR: Skill path {path} does not exist")
            sys.exit(1)
            
        skill_md = os.path.join(path, "SKILL.md")
        if not os.path.exists(skill_md):
            print(f"ERROR: SKILL.md missing in {path}")
            sys.exit(1)
            
        with open(skill_md) as smd:
            content = smd.read()
            if not content.startswith("---"):
                print(f"ERROR: Missing YAML frontmatter in {skill_md}")
                sys.exit(1)
                
    if entrypoints != 1:
        print(f"ERROR: Expected exactly 1 entrypoint, found {entrypoints}")
        sys.exit(1)
        
    print("Marketplace validation passed.")
    
if __name__ == "__main__":
    main()
