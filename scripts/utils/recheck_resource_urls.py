"""
Script: recheck_resource_urls.py

Purpose:
    This script loads a list of resources from resources.json, checks the validity of each resource's website URL,
    and updates the resource list with the results. It attempts to verify each URL by making HTTP HEAD requests,
    and if the specific URL fails, it tries the root domain. The script is useful for cleaning and validating
    resource data before further analysis or reporting.

Usage:
    python recheck_resource_urls.py <project_subdirectory>
    - <project_subdirectory> should contain config.yaml and resources.json.

Outputs:
    - resources.json: Updated with "url_valid" flags and possibly corrected website URLs.

Dependencies:
    - Python 3.x
    - requests
    - python-docx
    - treelib
    - openai
    - pyyaml

"""

import json
from urllib.parse import urlparse
import sys
import os
import yaml
import requests
from datetime import datetime

config = None
path = None

stage_name = "r"

# Aliases for mapping various possible keys in resource dicts to standard keys
aliases = {
    "program": [
        "name", "Name", "program_name", "program", "event_name", "title", "Effort Name", "EffortName", "Effort",
        "effort_name", "project_name", "Project Name", "description", "effort_description", "EffortDescription",
        "Effort_Name", "ProgramName", "ProjectName", "effort"
    ],
    "description": [
        "description", "Description", "effort_description", "effort", "EffortDescription"
    ],
    "organization": [
        "organization", "Organization", "address", "Organization", "ImplementingOrganization", "OrganizationName", "Address"
    ],
    "address": ["address", "Address"],
    "email": ["email", "Email", "email unavailable"],
    "website": ["website", "Website", "web_page", "webpage", "WebPage", "Web Page"],
    "id": ["id"],
}

def get_value(key, d):
    """
    Retrieve the value for a given key from a resource dict, using aliases and handling nested structures.
    """
    for k in aliases[key]:
        if k in d:
            if type(d[k]) is not dict:
                return d[k]
            else:
                if key == 'address':
                    for address_key in ['location', 'central_location']:
                        if address_key in d[k]:
                            return d[k][address_key]
                    else:
                        print(f"No key '{key}' found in {d}")
                        return "N/A"

    if key == 'email':
        return 'N/A'
    
    # Handle organizations as a list
    if "organizations" in d:
        if key == 'organization':
            key = 'name'
        return ', '.join(o[key] for o in d["organizations"])

    # Handle nested organization dicts
    org = None
    if "organization" in d:
        org = d["organization"]
    else:
        try:
            org = get_value("organization", d)
        except RecursionError as e:
            print(e)

    if type(org) is dict:
        if key == "organization":
            val = org["name"]
        else:
            val = get_value(key, org)
            if val is None:
                print(f"No key '{key}' found in {d}")
                sys.exit(1)
        return val
    else:
        if key == "website" or key == "description":
            return "N/A"
        print(f"No key '{key}' found in {d}")
        return None

    return 'N/A'

def normalize_resource_list():
    """
    Normalize the resource list to standard keys and mark duplicates.
    """
    global resource_list
    dups = {}
    keys = [
        "id", "program", "description", "organization", "address", "email", "website"
    ]
    for i in range(len(resource_list)):
        elem = {}
        for k in keys:
            elem[k] = get_value(k, resource_list[i])
        dup_key = "|".join([elem["program"], elem["organization"]])
        if dup_key in dups:
            elem["dup"] = dups[dup_key]
        else:
            dups[dup_key] = elem["id"]
        resource_list[i] = elem

good_urls = {}

def check_website(url):
    """
    Check if a website URL is valid by making a HEAD request.
    If the specific URL fails, try the root domain.
    Returns the working URL or None if not valid.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
    }

    try:
        # First, try checking the specific URL
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=2)
        if response.status_code == 200:
            return url
        else:
            # If the specific page is not found, check the root URL
            root_url = "{uri.scheme}://{uri.netloc}/".format(uri=urlparse(url))
            response = requests.head(root_url, headers=headers, allow_redirects=True, timeout=2)
            if response.status_code == 200:
                print('200 base', root_url, url)
                return root_url
            else:
                print('failed retry', url)
                return None
    except requests.RequestException as e:
        # Any request exception means the URL is not valid
        return None

def re_check_urls():
    """
    Iterate through the resource list and re-check each website URL.
    Updates the "url_valid" field and corrects the website if needed.
    """
    global resource_list

    bad_urls = {}
    total_count = len(resource_list)
    count = 0
    for i in range(total_count):
        count += 1
        elem = resource_list[i]
        url = elem["website"]
        # Skip if url_valid is not present (never checked)
        if "url_valid" not in elem:
            continue
        else:
            # Skip if already marked valid or not a simple False
            if elem["url_valid"] == True:
                continue
            elif elem["url_valid"] != False:
                continue
        # Skip obviously invalid or placeholder URLs
        if " " in url or "N/A" in url or "Varies" in url or "n/a" in url or "TBD" in url:
            print('del:', url)
            del elem["url_valid"]
            continue
        
        if type(url) is not str:
            print('Need to fix non-str url', url)
            continue

        # Use http instead of https for checking (sometimes more lenient)
        url = url.replace('https','http')
        if url in bad_urls:
            print(f'{datetime.now().isoformat()} {count}/{total_count} {100*count/total_count:0.3g}% skipping bad {url}')
        else:
            print(f'{datetime.now().isoformat()} {count}/{total_count} {100*count/total_count:0.3g}% retrying {url}')
        ret_url = check_website(url)
        if ret_url is None:
            bad_urls[url] = 'bad'
        else:
            print(f'{datetime.now().isoformat()} {count}/{total_count} {100*count/total_count:0.3g}% 200 {ret_url}')
            elem["url_valid"] = True
            elem["website"] = ret_url

        resource_list[i] = elem

rcount = 0
resource_keys = {}

resource_list = []

def main():
    """
    Main entry point for the script.
    Loads config and resource list, checks URLs, and saves results.
    """
    global resource_list

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        return 1

    path = sys.argv[1]
    # Load configuration (not used in this script, but may be for future extensions)
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    # Load the resource list from resources.json
    with open(os.path.join(path, "resources.json"), "r", encoding='utf-8') as f:
        resource_list = json.load(f)

    print("re_check_urls")
    re_check_urls()

    # Save the updated resource list back to resources.json
    with open(os.path.join(path, "resources.json"), "w", encoding='utf-8') as f:
        json.dump(resource_list, f)

    return 0

if __name__ == "__main__":
    sys.exit(main())
