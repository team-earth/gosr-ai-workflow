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
    with open(os.path.join(path, filename), "w", encoding='utf-8') as f:
        json.dump(j, f)
    # print(json.dumps(j, indent=2))


# def add_resources(node):
#     # msg_text = f"Given this undesired issue: \"{node.tag}\" produce a list of possible solutions the community can contribute to."
#     # msg_text = f'Given this undesired issue: "{node.tag}" produce a list of possible solutions the community can contribute to, delineating the Israeli community, the Palestinian and Arab community, and the international community.'
#     # messages = [{"role": "user", "content": msg_text}]
#     # model = "gpt-3.5-turbo"
#     # text = robust_call(model, messages)
#     resources_list = get_resources(node)
#     index = len(global_resources_list)
#     for r in resources_list:
#         rr = r_normalize(r)
#         rr["id"] = index
#         index += 1
#         global_resources_list.append(rr)
#     node.tag = "solution"
#     for r in resources_list:
#         r_node = {"id": r["id"]}
#         tree.create_node(data=r_node, parent=node, tag="resource")


def get_profile(node, use_cache=True):
    global solution_categories
    #     text = f"""We want to list the efforts in {city}, {country} that implement this solution:
    # \"{node.data}\"
    # Can you list and describe each effort and then mention the organization implementing it, all in JSON format as a plain list of dicts? Include address, email, and website.
    # """
#     text = f"""We want to list existing efforts in {locality}, {country} that implement this solution:
# \"{node.data}\"
# Can you list and describe each real effort and then mention the organization implementing it, all in JSON format as a plain list of dicts? Include address, email, and valid web page.
# """
    text = f"""Use the following categories of evaluation: {solution_categories}.
Evaluate the following from 0 to 10 in each category: {node}.
Return a simple JSON only with rating numbers like this: {{ "evaluation": [ 1,2,3,4,5,6]}}."""

    total_data = []
    # print("Sending text:",text)
    omit_text = ""

    data = call_gpt4(text + omit_text, use_cache=use_cache)

    print("Data:", data)

    return data

def add_profile(node):
    global solution_categories
    d = {
        'program': node['program'],
        'description': node['description']
    }
    count = 0
    found = False
    use_cache = True
    while not found and count < 5:
        count += 1
        try:    
            rating = get_profile(d, use_cache)
            eval = rating["evaluation"]
            if len(eval) != len(solution_categories):
                raise ValueError(f"Rating is not len {len(solution_categories)}")
            if any(value < 0 for value in eval):
                raise ValueError("Negative value detected")
            node["eval"] = eval
        except Exception as e:
            print(node, d, rating, e)
            use_cache = False
        else:
            found = True

def save_resources():
    with open(os.path.join(path, "resources-eval.json"), "w", encoding='utf-8') as f:
        json.dump(global_resources_list, f)


def load_resources():
    global global_resources_list
    file_path = os.path.join(path, "resources.json")
    if os.path.exists(file_path) and os.access(file_path, os.R_OK):
        with open(file_path, "r", encoding='utf-8') as f:
            global_resources_list = json.load(f)

def open_cache(cache_path):
    "Open cache file"
    try:
        with open(cache_path, "r", encoding='utf-8') as f:
            utils.cache4 = json.load(f)
    except (IOError, OSError):
        print(f"No file {cache_path}")
    except json.JSONDecodeError:
        print(f"File not parsable: {cache_path}")

solution_categories = None

def main():
    "Main functionality"
    # global config, path
    global solution_categories, global_resources_list, cache_dirty

    solution_categories = config["solution_categories"]
    # country = config["country"]
    # max_resource_loops = config.get("max_resource_loops", max_resource_loops)

    cache_path = os.path.join(path, "cache-eval.json")
    open_cache(cache_path)

    # in_file = "s.json"
    # logger.info("loading existing %s" % in_file)
    # load_tree(os.path.join(path, in_file))
    logger.info("loading existing resources")
    load_resources()

    count = 0
    total_count = len(global_resources_list)
    for r in global_resources_list:
        count = count + 1
        print(f"{datetime.now().isoformat()} {count}/{total_count} {100*count/total_count:.3g}%", r)
        if "dup" in r:
            continue
        add_profile(r)
        # print_tree("root")
        # save_tree()
        if utils.cache_dirty:
            with open(cache_path, "w", encoding='utf-8') as f:
                json.dump(utils.cache4, f)
            utils.cache_dirty = False
        # debugging break
        # break
        # run_stats(global_resources_list)
    save_resources()

    # leaf_list = tree.leaves()
    # for n in leaf_list:
    # insert_causative(n)
    # print_tree("root")
    # print("Sleep 30")
    # time.sleep(30)

    # save_tree()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        sys.exit(1)

    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    log_filename = os.path.join(path, "s-eval.log")

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
