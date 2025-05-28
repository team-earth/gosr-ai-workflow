import openai
from treelib import Node, Tree
import json
import logging, logging.handlers
import sys
import time
import requests
import yaml
import os
import re
from utils import parse_to_nodes, robust_call, call_gpt4, load_tree, tree
from r_stats import run_stats, r_normalize, get_program_value, get_organization_value

logger = logging.getLogger()

config = None
path = None

global_resources_list = []

city = "London"
country = "England"
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


def save_tree(filename="r.json"):
    j = json.loads(tree.to_json(with_data=True))
    with open(os.path.join(path, filename), "w", encoding='utf-8') as f:
        json.dump(j, f)
    # print(json.dumps(j, indent=2))


# def add_children(parent, d):
#     #   print (d['children'])
#     for c in d["children"]:
#         if type(c) is dict:
#             node_key = list(c.keys())[0]
#             n = tree.create_node(node_key, parent=parent)

#             # tree.create_node(d.keys()[0], parent=parent)
#             add_children(n, c[node_key])
#         else:
#             n = tree.create_node(c, parent=parent, data="obstacle")


# def load_tree(filename="s.json"):
#     with open(os.path.join(path, filename), "r", encoding='utf-8') as f:
#         d = json.load(f)

#     tree = Tree()
#     # print(d.keys()[0])
#     node_key = list(d.keys())[0]
#     n = tree.create_node(node_key, "root", data="obstacle")

#     add_children(n, d[node_key])
#     # print(json.dumps(j, indent=2))


def add_resources(node):
    # msg_text = f"Given this undesired issue: \"{node.tag}\" produce a list of possible solutions the community can contribute to."
    # msg_text = f'Given this undesired issue: "{node.tag}" produce a list of possible solutions the community can contribute to, delineating the Israeli community, the Palestinian and Arab community, and the international community.'
    # messages = [{"role": "user", "content": msg_text}]
    # model = "gpt-3.5-turbo"
    # text = robust_call(model, messages)
    resources_list = get_resources(node)
    index = len(global_resources_list)
    for r in resources_list:
        rr = r_normalize(r)
        rr["id"] = index
        index += 1
        global_resources_list.append(rr)
    node.tag = "solution"
    for r in resources_list:
        tree.create_node(data=r, parent=node, tag="resource")
    # id = node.identifier
    # n = tree.get_node(id)
    # x = tree.show(stdout=False, sorting=False, )
    # print(x)
    # j = tree.to_json(with_data=True, sort=False)
    # logger.info(json.dumps(json.loads(j), indent=2))


def get_resources(node):
    global city, country
    text = f"""We want to list the efforts in {city}, {country} that implement this solution:
\"{node.data}\"
Can you list and describe each effort and then mention the organization implementing it, all in JSON format as a plain list of dicts? Include address, email, and website.
"""
    data = {
        "efforts": [
            {
                "name": "Inclusive Curriculum Initiative",
                "description": "An advocacy initiative to push for the integration of educational materials covering the topic of extremism and its impact on communities within the Ottawa-Carleton District School Board (OCDSB). The program aims to prepare students to critically evaluate extremist narratives and understand the importance of diversity and inclusion.",
                "organization": "Ottawa-Carleton District School Board (OCDSB)",
                "address": "133 Greenbank Road, Ottawa, Ontario K2H 6L3",
                "email": "communications@ocdsb.ca",
                "website": "https://www.ocdsb.ca/",
            },
            {
                "name": "University Awareness Programs",
                "description": "Collaborations between university student associations and faculty to include courses and workshops that address the identification of extremist tactics and their societal impacts. These programs are designed to empower students with the knowledge to engage constructively in diverse communities.",
                "organization": "University of Ottawa",
                "address": "75 Laurier Ave E, Ottawa, ON K1N 6N5",
                "email": "info@uottawa.ca",
                "website": "https://www.uottawa.ca/",
            },
            {
                "name": "Community Resilience Fund",
                "description": "A fund that supports local projects aimed at countering radicalization to violence. This includes initiatives to improve education on extremist influences through the development of specialized curricula.",
                "organization": "Public Safety Canada",
                "address": "269 Laurier Avenue West, Ottawa, Ontario K1A 0P8",
                "email": "publicsafety.canada@canada.ca",
                "website": "https://www.publicsafety.gc.ca/",
            },
            {
                "name": "Youth Empowerment Program",
                "description": "A program designed to give young people in Ottawa the tools to understand and respond to extremist messaging. This includes workshops and seminars as part of the school curriculum.",
                "organization": "Ottawa Police Service",
                "address": "474 Elgin St, Ottawa, ON K2P 2J6",
                "email": "community_police@ottawapolice.ca",
                "website": "https://www.ottawapolice.ca/",
            },
        ],
        "note": "This is a note",
    }

    total_data = []
    omit_list = []

    omit_text = ""

    for i in range(0, max_resource_loops):
        data = call_gpt4(text + omit_text)

        if type(data) is list and len(data) > 0:
            logger.info(f"data is list type, converting to dict")
            data = {"wrap_list": data}

        if type(data) is dict:
            # one single resource dict (or error)
            if (
                get_program_value(data) is not None
                and get_organization_value(data) is not None
            ):
                total_data.extend([data])
                break
            elif "status" in data and data["status"] == "error":
                break
            elif (
                len(data.keys()) == 0 or type(data[next(iter(data.keys()))]) is not list
            ):
                logger.warning(f"unknown data value returned: {type(data.values())}")
                break
            for k, v in data.items():
                if type(v) is list:
                    # total_data.extend(next(iter(data.values())))
                    total_data.extend(v)
                elif type(v) is dict:
                    if (
                        get_program_value(v) is not None
                        and get_organization_value(v) is not None
                    ):
                        total_data.extend([v])
                else:
                    logger.info(f"ignoring non-list, non-program dict {k}, {v}")
            omit_list = [d["name"] for d in total_data if "name" in d.keys()]
            omit_text = (
                "Please omit the following, since we already know about them: "
                + ", ".join(omit_list)
            )

    return total_data


def save_resources():
    with open(os.path.join(path, "resources.json"), "w", encoding='utf-8') as f:
        json.dump(global_resources_list, f)


def read_config(path):
    global config
    global city, country, max_resource_loops
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    city = config["city"]
    country = config["country"]
    max_resource_loops = config.get("max_resource_loops", max_resource_loops)


def fix_s(j_orig):
    global config
    j = {"goal": {"data": config["root_node_name"], "children": []}}

    for o1 in j_orig[next(iter(j_orig.keys()))]["children"]:
        new_o1 = {"obstacle": {"data": next(iter(o1.keys())), "children": []}}
        j["goal"]["children"].append(new_o1)

        for o2 in o1[next(iter(o1.keys()))]["children"]:
            new_o2 = {"obstacle": {"data": next(iter(o2.keys())), "children": []}}
            new_o1["obstacle"]["children"].append(new_o2)

            for o3 in o2[next(iter(o2.keys()))]["children"]:
                new_o3 = {"obstacle": {"data": next(iter(o3.keys())), "children": []}}
                new_o2["obstacle"]["children"].append(new_o3)

    return j


global_tree = Tree()


def convert_to_tree(d, parent=None):
    global global_tree
    if type(d) is dict:
        node_key = next(iter(d.keys()))
        n = global_tree.create_node(parent=parent, data=node_key, tag="obstacle")
        if "children" in d[node_key]:
            for c in d[node_key]["children"]:
                convert_to_tree(c, n)
    elif type(d) is str:
        n = global_tree.create_node(parent=parent, data=d, tag="obstacle")


def fix_tags():
    global global_tree
    for n in global_tree.leaves():
        n.tag = "solution"
    global_tree.get_node(global_tree.root).tag = "goal"


def main():
    global global_tree
    global config, path
    global city, country, max_resource_loops

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        return 1

    path = sys.argv[1]
    read_config(path)

    # load_tree(os.path.join(path, "s-orig.json"))
    with open(os.path.join(path, "s-orig.json"), "r", encoding="utf8") as file:
        j_orig = json.load(file)

    convert_to_tree(j_orig)

    # log_filename = os.path.join(path, "s2r.log")

    logger.setLevel(logging.DEBUG)

    handler = logging.handlers.RotatingFileHandler(
        filename="s-orig.log", maxBytes=0, backupCount=5, encoding="utf-8"
    )
    # if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
    #     # Rotate the log file
    #     handler.doRollover()

    logger.addHandler(handler)

    # j = fix_s(j_orig)
    fix_tags()

    with open(os.path.join(path, "s.json"), "w", encoding="utf8") as file:
        file.write(global_tree.to_json(with_data=True, sort=False))


if __name__ == "__main__":
    sys.exit(main())
