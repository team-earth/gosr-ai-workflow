import sys
import os
import yaml
import json
import csv
import re
# import pandas as pd

def find_nesting_level(d, level=1):
    if isinstance(d, dict):
        if not d:
            return level
        # if level == 5:
        #     print("dict:",d)
        return max(find_nesting_level(v, level + 1) for v in d.values())
    elif isinstance(d, list):
        if not d:
            return level
        # if level == 5:
        #     print("list",d)
        return max(find_nesting_level(i, level + 1) for i in d)
    else:
        return level

custom_fields = {}
categories = {}

def convert_categories(cats):
    global categories
    if cats == '':
        return ''
    cs = []
    split_cats = re.split(r'[ ,]+', cats)
    for cat in split_cats:
        if cat not in categories:
            print("Cat not in categories", cat)
            continue
        cs.append(categories[cat])
    return '|'.join(cs)

def convert_marker_to_dict(m):
    global custom_fields

    cf = m.get("custom_fields_data", [])

    d = dict(
        id=m["id"],
        title=m["title"],
        address=m["address"],
        description=m["description"],
        link=m["link"],
        category=convert_categories(m["category"])
        )
    
    for c in cf:
        # custom_fields[c["name"]] = c["id"]
        d[c["name"]] = c["value"]

    return d

def main():
    global custom_fields, categories

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        return 1

    path = sys.argv[1]
    # with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
    #     config = yaml.safe_load(file)

    wp_go_maps_dir = "WP_GO_MAPS"
    os.makedirs(os.path.join(path,wp_go_maps_dir), exist_ok=True)
    kc_map_input_file = os.path.join(wp_go_maps_dir, "kccommongood.wpgooglemaps.2024-06-01.json")

    with open(os.path.join(path,kc_map_input_file), 'r', encoding='utf-8') as in_file:
        kc_map = json.load(in_file)

    # Set customfields
    for cf in kc_map["customfields"]:
        custom_fields[cf["name"]] = cf["id"]

    for c in kc_map["categories"]:
        categories[c["id"]] = c["category_name"]

    marker_dicts = []
    for m in kc_map["markers"]:
        d = convert_marker_to_dict(m)
        marker_dicts.append(d)
    
    fieldnames = list(marker_dicts[0].keys())
    for k in custom_fields.keys():
        if k not in fieldnames:
            fieldnames.append(k)

    with open(os.path.join(path,"output.csv"), 'w', newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(marker_dicts)

    with open(os.path.join(path,"custom_fields.csv"), 'w', newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['name','id'])
        for k,v in custom_fields.items():
            writer.writerow([k,v])

    with open(os.path.join(path,"categories.csv"), 'w', newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['id','category_name'])
        for k,v in categories.items():
            writer.writerow([k,v])

if __name__ == "__main__":
    sys.exit(main())