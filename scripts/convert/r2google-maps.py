"""
Script: r2google-maps.py

Purpose:
    Extracts all resources from a hierarchical resource tree (r.json) and resource list (resources.json),
    and generates CSV files suitable for Google Maps import and mailing lists. Each top-level theme
    (obstacle) gets its own CSV, and a combined mailing_list.csv is also produced.

Workflow:
    1. Loads configuration and resource list from the specified project directory.
    2. Loads the hierarchical resource tree (r.json).
    3. Traverses the tree to collect all resources, associates them with their solution and obstacle.
    4. Cleans and normalizes resource data, including URLs.
    5. Writes a CSV for each top-level theme and a combined mailing list CSV.

Usage:
    python r2google-maps.py <project_subdirectory>
    - <project_subdirectory> should contain config.yaml, r.json, and resources.json.

Outputs:
    - Google Maps/<theme>.csv: CSV files for each top-level theme.
    - mailing_list.csv: Combined CSV of all unique resources with category.

Dependencies:
    - Python 3.x
    - pyyaml

See the project README for more details.
"""

import json
import re
import sys
import os
import yaml
import csv
from html import escape

config = None
path = None

doc = None  # Placeholder, not used in this script

def open_tree(filename):
    """
    Load a tree structure from a JSON file in the project directory.
    """
    with open(os.path.join(path, filename), 'r', encoding='utf-8') as f:
        j = json.load(f)
    return j

def write_node(n, indent=0):
    """
    Recursively write a node and its children as XML nodes (not used in this script).
    """
    s = ""
    if type(n) == dict:
        for k, v in n.items():
            s += f'{"  "*indent}<node TEXT="{escape(k)}">\n'
            for c in v['children']:
                s += write_node(c, indent+2)
            s += f'{"  "*indent}</node>\n'
    elif type(n) == str:
        s += f'{"  "*indent}<node TEXT="{escape(n)}"></node>\n'
    return s

aliases = {
    "name": [
        "name", "Name", "program_name", "program", "event_name", "title", "Effort Name", "EffortName", "Effort",
        "effort_name", "project_name", "description", "effort_description", "EffortDescription", "Effort_Name",
        "ProgramName", "ProjectName", "effort"
    ],
    "description": ["description", "Description", "effort_description", "effort", "EffortDescription"],
    "organization": ["organization", "address", "Organization", "ImplementingOrganization", "OrganizationName"],
    "address": ["address", "Address"],
    "email": ["email", "Email", "email unavailable"],
    "website": ["website", "Website"]
}

def get_value(key, d):
    """
    Get a value for a standard key from a resource dict, handling nested orgs.
    """
    for k in aliases[key]:
        if k in d:
            return d[k]
    if 'organizations' in d:
        if key == 'organization':
            return d['organizations'][0]['name']
        if key == 'address':
            return d['organizations'][0]['address']
        if key == 'email':
            return d['organizations'][0]['email']
        if key == 'website':
            return d['organizations'][0]['website']
    if key == 'name':
        return d['organization']['name']
    if key == 'address':
        return d['organization']['address']
    if key == 'email':
        return d['organization']['email']
    if key == 'website':
        return d['organization']['website']
    print(f"No key '{key}' found in {d}")
    sys.exit(1)

resource_list = []

def find_by_id(id):
    """
    Find a resource in the resource list by its ID, following duplicates if needed.
    """
    global resource_list
    for k in resource_list:
        if k["id"] == id:
            if "dup" in k:
                return find_by_id(k["dup"])
            else:
                return k
    return None

def get_all_resources(j, parent):
    """
    Recursively collect all resources from the tree, associating them with their solution and obstacle.
    """
    global resource_list
    rs = []
    key = list(j.keys())[0]
    if key == "solution":
        if "children" in j[key]:
            for r in j[key]["children"]:
                resource = find_by_id(r["resource"]["data"]["id"])
                solving_dict = parent["obstacle"]["data"]
                if type(solving_dict) == dict:
                    solving = solving_dict["title"].rstrip('. ')+'. '+solving_dict["description"].rstrip('. ')+'.'
                else:
                    solving = solving_dict
                solution_dict = j[key]["data"]
                if type(solution_dict) == dict:
                    solution = solution_dict["title"].rstrip('. ')+'. '+solution_dict["description"].rstrip('. ')+'.'
                else:
                    solution = solution_dict
                resource["solving"] = solving
                resource["solution"] = solution
                # Clean up URLs
                if "url_valid" in resource:
                    if resource["url_valid"] == False:
                        del resource["url_valid"]
                        resource["website"] = "N/A"
                    elif resource["url_valid"] == True:
                        del resource["url_valid"]
                    else:
                        resource["website"] = resource["url_valid"]
                        del resource["url_valid"]
                rs.append(resource)
        return rs
    else:
        for c in j[key]["children"]:
            rs.extend(get_all_resources(c, j))
        return rs

def main():
    """
    Main entry point for the script.
    Loads config and resource list, extracts resources, and writes CSVs for Google Maps and mailing lists.
    """
    global config
    global path
    global resource_list

    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} path')
        return 1

    path = sys.argv[1]
    with open(os.path.join(path, 'config.yaml'), 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)

    with open(os.path.join(path, "resources.json"), "r", encoding='utf-8') as f:
        resource_list = json.load(f)

    with open(os.path.join(path, 'r.json'), 'r', encoding='utf-8') as f:
        j = json.load(f)

    r_all = []
    unique = []

    # For each top-level theme (obstacle), extract resources and write a CSV
    for top_level_theme in j["goal"]["children"]:
        if "label" in top_level_theme["obstacle"]:
            theme = top_level_theme["obstacle"]["label"]
        else:
            theme = top_level_theme["obstacle"]["data"]["title"]
        r = get_all_resources(top_level_theme, None)

        filename = theme.strip()
        filename = re.sub(r'/', ', ', filename)
        filename = re.sub(r':', ' - ', filename)
        filename = re.sub(r'[^a-zA-Z0-9_.-]', ' ', filename)
        filename = re.sub(r'  +', ' ', filename)

        os.makedirs(os.path.join(path, "Google Maps"), exist_ok=True)
        with open(os.path.join(path, "Google Maps", f"{filename}.csv"), "w", newline='\n', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=r[0].keys())
            writer.writeheader()
            writer.writerows(r)

        for d in r:
            if d["id"] not in unique:
                unique.append(d["id"])
                d_copy = d.copy()
                d_copy.update({'category': theme})
                r_all.append(d_copy)

    # Write a combined mailing list CSV
    with open(os.path.join(path, "mailing_list.csv"), "w", newline='\n', encoding='utf-8') as csvfile:
        header = list(r_all[0].keys())
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        writer.writerows(r_all)
    return 0

if __name__ == '__main__':
    sys.exit(main())