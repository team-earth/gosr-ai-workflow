"""
Script: json2mm.py

Purpose:
    Converts a hierarchical JSON tree (such as s.json or r.json) into a FreeMind mind map (.mm) XML file.
    Useful for visualizing solution/resource trees in FreeMind or compatible tools.

Workflow:
    1. Loads configuration from config.yaml in the specified project directory.
    2. Loads the hierarchical tree structure (e.g., s.json or r.json).
    3. Recursively writes the tree as FreeMind XML nodes, handling both regular and resource nodes.
    4. Saves the resulting .mm file to the project directory.

Usage:
    python json2mm.py <project_subdirectory> --stage <stage>
    - <project_subdirectory> should contain config.yaml and s.json/r.json.
    - <stage> should be 'r' for resources or 's' for solutions.

Outputs:
    - <stage>.mm: FreeMind mind map file representing the tree.

Dependencies:
    - Python 3.x
    - pyyaml

See the project README for more details.
"""

import json
import sys
import logging
import os
import yaml
from html import escape
import argparse

config = None
path = None

def open_tree(filename):
    """
    Load a tree structure from a JSON file in the project directory.
    """
    with open(filename, 'r', encoding='utf8') as f:
        j = json.load(f)
    return j

count = 0

def write_node(n, indent=0):
    """
    Recursively write a node and its children as FreeMind XML nodes.
    Handles both regular nodes and resource nodes.
    """
    global count
    s = ""
    if type(n) == dict:
        for k, v in n.items():
            if k != 'resource':
                s += f'{"  "*indent}<node TEXT="' + escape(v['data']) + '">\n'
                if "children" in v:
                    for c in v['children']:
                        s += write_node(c, indent+2)
                s += f'{"  "*indent}</node>\n'
            else:
                count += 1
                content = escape(v['data'].get('name', 'Noname') + ' | ' + v['data']['description'])
                s += f'{"  "*indent}<node TEXT="R:' + content + '">\n'
                s += f'{"  "*indent}</node>\n'
    elif type(n) == str:
        s += f'{"  "*indent}<node TEXT="{escape(n)}"></node>\n'
    return s

def write_tree(d, filename):
    """
    Write the entire tree as a FreeMind mind map (.mm) file.
    """
    s = ""
    s += '<map version="1.0.1">\n'
    s += write_node(d)
    s += "</map>\n"
    with open(filename, 'w', encoding="utf8") as f:
        f.write(s)

def main():
    """
    Main entry point for the script.
    Loads config and tree, writes the mind map file.
    """
    global config
    global path

    parser = argparse.ArgumentParser(description="Convert a JSON tree to a FreeMind mind map (.mm) file.")
    parser.add_argument("path", help="Project directory containing config.yaml and s.json/r.json")
    parser.add_argument("--stage", choices=["r", "s"], required=True, help="Stage name: 'r' for resources, 's' for solutions (required)")
    args = parser.parse_args()

    path = args.path
    stage = args.stage

    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    logging.basicConfig(
        filename=os.path.join(path, "json2mm.log"), encoding="utf-8", level=logging.DEBUG
    )

    input_filename = f"{stage}.json"
    j = open_tree(filename=os.path.join(path, input_filename))
    logging.info(json.dumps(j, indent=2))

    output_filename = f"{stage}.mm"
    write_tree(j, filename=os.path.join(path, output_filename))

if __name__ == '__main__':
    sys.exit(main())