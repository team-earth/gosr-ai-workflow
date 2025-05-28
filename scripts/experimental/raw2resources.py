import docx
import docx
import openai
from treelib import Node, Tree
import json
from urllib.parse import urlparse

# import codecs
# import re
import sys
import time
from html import escape
import os
import yaml
import csv
import requests
from datetime import datetime

config = None
path = None

stage_name = "r"
doc = docx.Document()

aliases = {
    "program": [
        "name",
        "Name",
        "program_name",
        "program",
        "event_name",
        "title",
        "Effort Name",
        "EffortName",
        "Effort",
        "effort_name",
        "project_name",
        "Project Name",
        "description",
        "effort_description",
        "EffortDescription",
        "Effort_Name",
        "ProgramName",
        "Program Name",
        "ProjectName",
        "effort",
        "Title",
    ],
    "description": [
        "description",
        "Description",
        "effort_description",
        "effort",
        "EffortDescription",
    ],
    "organization": [
        "organization",
        "Organization",
        "address",
        "Organization",
        "ImplementingOrganization",
        "OrganizationName",
        "Address"
    ],
    "address": ["address", "Address"],
    "email": ["email", "Email", "email unavailable"],
    "website": ["website", "Website", "web_page", "webpage", "WebPage", "Web Page"],
    "id": ["id"],
}

def get_value(key, d):
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
    
    if "organizations" in d:
        if key == 'organization':
            key = 'name'
            return ', '.join(o[key] for o in d["organizations"])

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
    global resource_list
    dups = {}
    keys = [
        "id",
        "program",
        "description",
        "organization",
        "address",
        "email",
        "website",
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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    try:
        # First, try checking the specific URL
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
        if response.status_code == 200:
            print('200 original', url)
            return url
        else:
            # If the specific page is not found, check the root URL
            root_url = "{uri.scheme}://{uri.netloc}/".format(uri=urlparse(url))

            if root_url in good_urls and root_url == good_urls[root_url]:
                print('previously good base', root_url, url)
                return root_url

            response = requests.head(root_url, headers=headers, allow_redirects=True, timeout=5)
            if response.status_code == 200:
                print('200 base', root_url, url)
                return root_url
            else:
                print('invalid retry', url)
                return None
    except requests.RequestException:
        print('request exception', url)
        return None

def check_urls():
    global resource_list

    total_count = len(resource_list)
    count = 0
    for i in range(total_count):
        count += 1
        # progress = f'{count}/{total_count} {100*count/total_count:0.3g}%'
        progress = f"{datetime.now().isoformat()} {count}/{total_count} {100*count/total_count:.3g}%"
        print(progress)
        elem = resource_list[i]
        url = elem["website"]
        if "url_valid" in elem and elem["url_valid"] == True:
            print('Skipping valid', url)
            continue
        if type(url) is str:
            if url in good_urls:
                if url == good_urls[url]:
                    print('previously good', url)
                    continue
                elif good_urls[url] == False:
                    print('previously bad', url)
                    elem["url_valid"] = False
                else:
                    print('previously good base', good_urls[url], url)
                    elem["url_valid"] = good_urls[url]
            else:
                ret_url = check_website(url)
                if ret_url is None:
                    elem["url_valid"] = False
                else:
                    good_urls[url] = ret_url
                    good_urls[ret_url] = ret_url
                    elem["website"] = ret_url
                    elem["url_valid"] = True

            resource_list[i] = elem


rcount = 0
resource_keys = {}

resource_list = []


def main():
    global resource_list

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        return 1

    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    with open(os.path.join(path, "resources-raw.json"), "r", encoding='utf-8') as f:
        resource_list = json.load(f)

    print("normalize")
    normalize_resource_list()

    print("check_urls")
    check_urls()

    with open(os.path.join(path, "resources.json"), "w", encoding='utf-8') as f:
        json.dump(resource_list, f)

    return 0


if __name__ == "__main__":
    sys.exit(main())
