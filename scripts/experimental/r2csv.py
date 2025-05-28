import openai
from treelib import Node, Tree
import json

# import codecs
# import re
import sys
import time
from html import escape
import logging, logging.handlers
import os
import yaml
import csv

logger = logging.getLogger("r_stats")
logger.setLevel(logging.INFO)


def open_tree(filename):
    with open(filename, "r", encoding='utf-8') as f:
        j = json.load(f)
    return j


def write_node(n, indent=0):
    s = ""

    if type(n) == dict:
        for k, v in n.items():
            s += f'{"  "*indent}<node TEXT="{escape(k)}">\n'
            for c in v["children"]:
                s += write_node(c, indent + 2)
            s += f'{"  "*indent}</node>\n'
    elif type(n) == str:
        s += f'{"  "*indent}<node TEXT="{escape(n)}"></node>\n'

    return s


def write_tree(d, filename):
    s = ""
    s += '<map version="1.0.1">\n'
    s += write_node(d)
    s += "</map>\n"
    with open(filename, "w", encoding='utf-8') as f:
        f.write(s)


aliases = {
    "name": [
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
        "description",
        "effort_description",
        "EffortDescription",
        "Effort_Name",
        "ProgramName",
        "ProjectName",
        "effort"
    ],
    "description": ["description", "Description", "effort_description", "effort", "EffortDescription"],
    "organization": ["organization", "address", "Organization", "ImplementingOrganization", "OrganizationName"],
    "address": ["address", "Address"],
    "email": ["email", "Email", "email unavailable"],
    "website": ["website", "Website"]
}


def get_value(key, d):
    for k in aliases[key]:
        if k in d:
            return d[k]

    if key == 'name':
        return d['organization']['name']
    if key == 'address':
        return d['organization']['address']
    if key == 'email':
        return d['organization']['email']
    if key == 'website':
        return d['organization']['website']
    logger.error(f"No key '{key}' found in {d}")
    sys.exit(0)


def normalize(j):
    n = []
    orgs = {}
    programs = {}
    for i in j:
        elem = {}
        for k in aliases.keys():
            elem[k] = get_value(k,i)
        n.append(elem)
    return n

def main():
    global config
    global path

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        return 1

    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    # log_filename = os.path.join(path, "r_stats.log")

    # handler = logging.handlers.RotatingFileHandler(
    #     filename=log_filename, maxBytes=0, backupCount=5
    # )
    # if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
    #     # Rotate the log file
    #     handler.doRollover()

    # logger.addHandler(handler)

    input_filename = "resources-map.json"

    j = open_tree(filename=os.path.join(path, input_filename))
    # logger.info(json.dumps(j, indent=2))
    n = normalize(j)
    with open(os.path.join(path,"resources-map.csv"), "w", newline='\n', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=j[0].keys())
        writer.writeheader()
        writer.writerows(n)
    print(len(n))


if __name__ == "__main__":
    sys.exit(main())
