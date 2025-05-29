from utils import setup_openai
setup_openai()

import openai
from openai import OpenAI

client = OpenAI(api_key=openai.api_key, organization=openai.organization)
from treelib import Node, Tree
import json
import logging
import sys
import time
import requests
import re
import hashlib

logger = logging.getLogger(__name__)
config = None
path = None
cache4 = {}

tree = Tree()


def next_number(curr_parent_name):
    for i in range(1, 100):
        trial = ".".join([curr_parent_name, str(i)])
        if tree.get_node(trial) is None:
            return str(i)


def dehyphenate(text):
    return text

title_keys = [
    "obstacle",
    "Factor",
    "factor",
    "solution_title",
    "strategy",
    "approach",
    "title",
    "solution",
    "name",
    "      title",
    "     title",
    "action",
    "WrappedTextarea-title",
    "solutionTitle",
]

description_keys = [
    "description",
    "Description",
    "solution_description",
    "details",
    "      description",
    "detail",
    "Details",
    "solutionDescription",
    "explanation"
]

contributing_factors = [
    "obstacle",
    "contributing_factors",
    "Contributing Factors",
    "Contributing_Factors"
]
def get_title_and_description_keys(d):
    description_reconciliation_keys = ["detail", "details"]
    id_keys = ["solution_id", "id"]
    title_key = None
    description_key = None
    id_key = None
    for k in d.keys():
        if k.strip() in title_keys:
            if title_key is None:
                title_key = k
        elif k.strip() in description_keys:
            if description_key is None:
                description_key = k
            else:
                if k in description_reconciliation_keys:
                    title_key = description_key
                    description_key = k
                elif description_key in description_reconciliation_keys:
                    title_key = k
        elif k in id_keys:
            id_key = k
    if title_key is None and id_key is None:
        logger.warning(f"No title_key or id_key in {d.keys()}")
    if description_key is None:
        logger.error(f"No description_key in {d.keys()}")
    return title_key, description_key

def normalize_dict(data):
    title_key = None
    description_key = None

    keys = list(data.keys())
    if "description" in keys and "detail" in keys:
        title_key = "description"
        description_key = "detail"
    
    contributing_factor_keys = list(set(keys).intersection(set(contributing_factors)))
    if len(contributing_factor_keys) == 1:
        return normalize_data(data[contributing_factor_keys[0]])
    else:
        for k in keys:
            if k in title_keys:
                title_key = k
            elif k in description_keys:
                description_key = k

    if title_key is None and description_key is None:
        if len(data) == 1:
            elem = {
                "title": keys[0].replace('_', ' '),
                "description": data[keys[0]]
            }
            return elem
        else:
            l = []
            for k, v in data.items():
                l.append({"title": k.replace('_', ' '), "description": v})
            return l

    if title_key is None or description_key is None:
        sys.exit(1)

    elem = {
        "title": data[title_key].replace('_', ' '),
        "description": data[description_key]
    }
    return elem

def normalize_list(data):
    l = []
    for d in data:
        if type(d) is dict:
            l.append(normalize_dict(d))
    return l

def normalize_data(data):
    if type(data) is list:
        return normalize_list(data)
    if type(data) is dict:
        if len(data) == 1:
            key = next(iter(data.keys()))
            return normalize_data(data[key])
        else:
            return normalize_dict(data)
    return data
    

def get_obstacle_list(data):
    if type(data) is list:
        return data
    if type(data) is dict:
        if len(data) == 1:
            key = next(iter(data.keys()))
            return get_obstacle_list(data[key])
        elif len(data) == 2:
            for k, v in data.items():
                if k not in ['obstacle', 'issue']:
                    return get_obstacle_list(v)
        else:
            obstacle_list = []
            for k, v in data.items():
                obstacle_list.append({"title": k, "description": v})
            return obstacle_list

    logger.error(f"No obstacle list at {data}")
    return None


def insert_nodes(parent_name, data, tag):
    """We assume tag is obstacle"""

    parent_node = tree.get_node(parent_name)

    obstacle_list = get_obstacle_list(data)
    logger.info(f"obstacle_list: {obstacle_list}")

    for o in obstacle_list:
        if type(o) is dict:
            if len(o) == 1:
                key = next(iter(o.keys()))
                d = o[key]

            elif len(o) >= 2:
                # expect obstacle and description
                d = o
            
            title_key, description_key = get_title_and_description_keys(d)

            if description_key is None:
                sys.exit(1)

            if title_key is None:
                data = d[description_key]
            else:
                data = {"title": d[title_key], "description": d[description_key]}

            logger.info(f"new node data: {data}")
            tree.create_node(
                data=data,
                parent=parent_node,
                tag=tag,
            )

    # if type(data) is list and len(data) > 0:
    #     logger.info(f"data is list type, converting to dict")
    #     data = {"wrap_list": data}
    # if type(data) is dict:
    #     # one single resource dict (or error)
    #     if (
    #         get_program_value(data) is not None
    #         and get_organization_value(data) is not None
    #     ):
    #         total_data.extend([data])
    #         break
    #     elif "status" in data and data["status"] == "error":
    #         break
    #     elif (
    #         len(data.keys()) == 0 or type(data[next(iter(data.keys()))]) is not list
    #     ):
    #         logger.warning(f"unknown data value returned: {type(data.values())}")
    #         break
    #     for k, v in data.items():
    #         if type(v) is list:
    #             # total_data.extend(next(iter(data.values())))
    #             total_data.extend(v)
    #         elif type(v) is dict:
    #             if (
    #                 get_program_value(v) is not None
    #                 and get_organization_value(v) is not None
    #             ):
    #                 total_data.extend([v])
    #         else:
    #             logger.info(f"ignoring non-list, non-program dict {k}, {v}")
    #     omit_list = [d["name"] for d in total_data if "name" in d.keys()]
    #     omit_text = (
    #         "Please omit the following, since we already know about them: "
    #         + ", ".join(omit_list)
    #     )


def parse_to_nodes(parent_name, text, tag):
    # print(tree.to_json())
    parent_node = tree.get_node(parent_name)
    parent_nodes = {}
    old_indentation = None

    logger.debug(text)
    lines = text.splitlines()
    # if not re.match(r"^(\d+|-|[A-Za-z]+\.)", lines[0]):
    #   lines = lines[1:]  # Skip the first line

    for line in lines:
        if line == "":
            continue
        if parent_node.data in line:
            continue

        line = re.sub(r"^(\d+)", r"  \1", line)
        line = re.sub(r"^-", " " * 4 + "-", line)
        new_indentation = len(re.match(r"\s*", line).group())
        content = re.sub(r"^\s*([\d\w]*[.)]\s*|-\s*)", "", line).strip()
        if old_indentation is None:
            old_indentation = new_indentation
            parent_nodes[new_indentation] = parent_node
        if new_indentation > old_indentation:
            parent_nodes[new_indentation] = prev_line_node
        old_indentation = new_indentation

        if new_indentation not in parent_nodes.keys():
            logger.info(f"Skipping line: {line}")
            continue

        number = next_number(parent_nodes[new_indentation].identifier)
        identifier = ".".join([parent_nodes[new_indentation].identifier, number])
        # identifier = identifier.replace('root.','')
        prev_line_node = tree.create_node(
            data=content,
            identifier=identifier,
            parent=parent_nodes[new_indentation],
            tag=tag,
        )


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
    logger.info(f"> {indent*'  '}{node.identifier}. {node.data}")
    for c in tree.children(identifier):
        print_tree(c.identifier, indent + 2)

cache_dirty = False

def call_gpt4(msg_text, use_cache=True):
    global cache4, cache_dirty
    
    hash_object = hashlib.md5()
    hash_object.update(msg_text.encode())
    key = hash_object.hexdigest()
    
    if use_cache and key in cache4:
        print("* ", end = "")
        return cache4[key]

    messages = [{"role": "user", "content": msg_text}]

    model = "gpt-4"
    model = "gpt-4-1106-preview"

    attempts = 0
    while attempts < 5:
        try:
            logger.debug(f'After one second sending: {messages[0]["content"]}')
            time.sleep(1)
            response = client.chat.completions.create(model=model,
            messages=messages,
            # request_timeout=120,
            # seed=32768,
            response_format={"type": "json_object"})
            text = response.choices[0].message.content
            logger.debug(f'Response: "{str(text).strip()}"')
            try:
                data = json.loads(text)
            except ValueError:
                logger.error(f'Can\'t translate string to JSON: "{text}"')
                return {}
            cache4[key] = data
            cache_dirty = True
            return data
        except (
            openai.RateLimitError,
            requests.exceptions.ConnectionError,
            # openai.error.APIError,
            # openai.error.Timeout,
            # openai.error.ServiceUnavailableError,
            # openai.error.APIConnectionError,
            requests.exceptions.ReadTimeout,
        ) as e:
            logger.warning(
                f"{type(e).__name__} encountered. New API call attempt in {(2**attempts)} seconds...\n{e}"
            )
        time.sleep((2**attempts))
        attempts += 1
    return f"No valid response from OpenAI API after {attempts} attempts!"


def add_children(parent, d):
    # print (d['children'])
    # x = tree.get_node("ROOT")
    if "children" in d:
        for c in d["children"]:
            if type(c) is dict:
                node_key = list(c.keys())[0]
                n = tree.create_node(node_key, parent=parent, data=c[node_key]["data"])

                # tree.create_node(d.keys()[0], parent=parent)
                add_children(n, c[node_key])
            else:
                n = tree.create_node(data=c.strip(), parent=parent, tag="obstacle")
    else:
        parent.data = d["data"]
        # n = tree.create_node(data=d["data"].strip(), parent=parent, tag="obstacle")


def load_tree(file_path):
    with open(file_path, "r", encoding='utf-8') as f:
        d = json.load(f)

    # print(d.keys()[0])
    node_key = list(d.keys())[0]
    n = tree.create_node(
        identifier="ROOT", data=d[node_key]["data"].strip(), tag="goal"
    )
    # print(d)
    add_children(n, d[node_key])
    logger.debug(json.dumps(tree.to_dict(with_data=True)))


# def robust_call(model, messages):
#     # return initial_response
#     attempts = 0
#     while attempts < 5:
#         try:
#             print("Sending:", messages[0]["content"])
#             response = client.chat.completions.create(model=model, messages=messages, request_timeout=120)
#             text = response.choices[0].message.content
#             print("Response:", text)
#             return text
#         except (
#             openai.RateLimitError,
#             requests.exceptions.ConnectionError,
#             openai.error.APIError,
#             openai.error.Timeout,
#             openai.error.ServiceUnavailableError,
#             openai.error.APIConnectionError,
#             requests.exceptions.ReadTimeout,
#         ) as e:
#             logger.warning(
#                 f"{type(e).__name__} encountered. New API call attempt in {(2**attempts)} seconds...\n{e}"
#             )
#             time.sleep((2**attempts))
#             attempts += 1
#     return f"No valid response from OpenAI API after {attempts} attempts!"


# def create_nodes():
#     root_question = config["root_question"]
#     messages = [{"role": "user", "content": root_question}]
#     model = "gpt-3.5-turbo"
#     text = robust_call(model, messages)
#     logger.info(root_question)
#     logger.info(text)
#     # print("Using prefetched text")
#     parse_to_nodes("root", text)


# def insert_causative(node):
#     msg_text = f'For item {node.identifier}, "{node.data}" produce a list of contributing factors in outline format and numbering.'
#     messages = [{"role": "user", "content": msg_text}]
#     model = "gpt-3.5-turbo"
#     text = robust_call(model, messages)
#     logger.info(msg_text)
#     logger.info(text)
#     # print("Result:\n",text)
#     parse_to_nodes(node.identifier, text)


def save_tree(filename="o.json"):
    j = json.loads(tree.to_json(with_data=True))
    with open(os.path.join(path, filename), "w", encoding='utf-8') as f:
        json.dump(j, f)


states = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", 
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", 
    "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", 
    "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", 
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
]

for state in states:
    msg_text = f"Create a list of resources for people who are seeking to be entrepreneurs in {state}. " + \
        "these resources should be project based and experiential. " + \
        "Include program name, link and a short description. include the physical address. Convert to CSV format from JSON."
    result = call_gpt4(msg_text, use_cache=False)
    print(result)