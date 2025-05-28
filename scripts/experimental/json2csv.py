from treelib import Node, Tree
import json
import logging, logging.handlers
import sys
import time
import yaml
import os
from utils import call_gpt4, load_tree, tree
from r_stats import run_stats, r_normalize, get_program_value, get_organization_value
import utils
from datetime import datetime
import random
import pandas as pd


logger = logging.getLogger()

config = None
path = None

global_resources_list = []

# city = "London"
# country = "England"
max_resource_loops = 1


def next_number(curr_parent):
    for i in range(1, 100):
        trial = ".".join([curr_parent, str(i)])
        if tree.get_node(trial) is None:
            return str(i)


def outline(children, indent=0):
    for c in children:
        if type(c) == str:
            print(f"{indent*'  '}{c}")
        elif type(c) == dict:
            for k, v in c.items():
                print(f"{indent*'  '}{k}")
                outline(v["children"], indent + 2)


def print_tree(identifier, indent=0):
    node = tree.get_node(identifier)
    logger.info(f"> {indent*'  '}> {node.data}")
    for c in tree.children(identifier):
        print_tree(c.identifier, indent + 2)


def save_tree(filename):
    j = json.loads(tree.to_json(with_data=True))
    with open(os.path.join(path, filename), "w", encoding="utf-8") as f:
        json.dump(j, f)
    # print(json.dumps(j, indent=2))

def get_profile(node, use_cache=True):
    global evaluation_categories
    text = f"""Use the following categories of evaluation: {evaluation_categories}.
Evaluate the following from 0 to 10 in each category: {node}.
Return rating numbers for each category and subcategory in a JSON dict that 
resembles the structure of the evaluation categories, where we just need the rating,
no description."""

    total_data = []
    # print("Sending text:",text)
    omit_text = ""

    data = call_gpt4(text + omit_text, use_cache=use_cache)

    # print("Data:", data)

    return data


def validate_eval(n):
    if len(eval) != 6:
        raise ValueError("Rating is not len 6")
    if any(value < 0 for value in n):
        raise ValueError("Negative value detected")


def compare_dict_structure(dict1, dict2):
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        if dict1.keys() == dict2.keys():
            for key in dict1:
                # Recursively compare the structure of nested dictionaries
                if not compare_dict_structure(dict1[key], dict2[key]):
                    return False
            return True
        else:
            return False
    elif not isinstance(dict1, dict) and not isinstance(dict2, dict):
        return False
    else:
        # One is a dict and the other is not
        return False

def save_resources():
    with open(os.path.join(path, "resources-score.json"), "w", encoding="utf-8") as f:
        json.dump(global_resources_list, f)


def load_resources(file_path):
    global global_resources_list
    if os.path.exists(file_path) and os.access(file_path, os.R_OK):
        with open(file_path, "r", encoding="utf-8") as f:
            global_resources_list = json.load(f)


def open_cache(cache_path):
    "Open cache file"
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            utils.cache4 = json.load(f)
    except (IOError, OSError):
        print(f"No file {cache_path}")
    except json.JSONDecodeError:
        print(f"File not parsable: {cache_path}")


evaluation_categories = None

def unpack_eval(e, v):
    global eval_categorization, score_categorization
    for i, d in enumerate(eval_categorization):
        e['.'.join(['eval', list(d.keys())[0]])] = v[i]

def unpack_score(e, v):
    for k1, v1 in v.items():
        for k2, v2 in v1.items():
            e['.'.join(['score',k1,k2])] = v2
            if v2 != int(v2):
                print(v2)

def json_flatten(js):
    flat = []

    for j in js:
        if "dup" in j:
            continue
        e = {}
        for k,v in j.items():
            if k == 'eval':
                unpack_eval(e, v)
            elif k == 'score':
                unpack_score(e, v)
            else:
                e[k] = v
        flat.append(e)
    return flat

def traverse_tree(rs, resource_dict):
    key = list(rs.keys())[0]
    value = rs[key]
    if key == 'resource':
        pass
    
    if 'children' in value:
        for c in value['children']:
            traverse_tree(c, resource_dict)

def main():
    "Main functionality"
    # global global_resources_list
    # if os.path.exists(file_path) and os.access(file_path, os.R_OK):
    #     with open(file_path, "r", encoding="utf-8") as f:
    #         global_resources_list = json.load(f)

    resource_path = os.path.join(path, "resources.json")
    if os.path.exists(resource_path) and os.access(resource_path, os.R_OK):
        with open(resource_path, "r", encoding="utf-8") as f:
            resources = json.load(f)

    resource_dict = {}
    for r in resources:
        resource_dict[r["id"]] = r

    resource_path = os.path.join(path, "r.json")
    if os.path.exists(resource_path) and os.access(resource_path, os.R_OK):
        with open(resource_path, "r", encoding="utf-8") as f:
            rs = json.load(f)
    
    traverse_tree(rs, resource_dict)


    load_resources(os.path.join(path, "resources.json"))
    flat_df = json_flatten(global_resources_list)
    df = pd.DataFrame(flat_df)
    print(df.head())
    df.to_csv(os.path.join(path, 'resources.csv'))

    print(df.head())
    count = 0
    total_count = len(global_resources_list)
    # for r in global_resources_list:

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        sys.exit(1)

    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    log_filename = os.path.join(path, "json2csv.log")

    logger.setLevel(logging.DEBUG)

    handler = logging.handlers.RotatingFileHandler(
        filename=log_filename, maxBytes=0, backupCount=5, encoding="utf-8"
    )
    if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
        # Rotate the log file
        handler.doRollover()

    logger.addHandler(handler)

    RETVAL = main()

    sys.exit(RETVAL)
