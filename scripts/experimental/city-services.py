import os
import openai
from treelib import Node, Tree
import json
import logging, logging.handlers
import sys
import time
import requests
import yaml
import re
from utils import parse_to_nodes, robust_call, tree, call_gpt4, insert_nodes, setup_openai, setup_logging

# Use the shared OpenAI setup function
setup_openai()

setup_logging("city-services.log", backup_count=5)
logger = logging.getLogger(__name__)

def next_number(curr_parent_name):
    for i in range(1, 100):
        trial = ".".join([curr_parent_name, str(i)])
        if tree.get_node(trial) is None:
            return str(i)


def dehyphenate(text):
    return text


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
    logger.info(f"> {indent*'  '}{node.identifier}. {node.tag} {node.data}")
    for c in tree.children(identifier):
        print_tree(c.identifier, indent + 2)


def create_nodes():
    root_question = config["root_question"]
    messages = [{"role": "user", "content": root_question}]
    model = "gpt-3.5-turbo"
    text = robust_call(model, messages)
    logger.info(root_question)
    logger.info(text)
    # print("Using prefetched text")
    parse_to_nodes("root", text, tag="obstacle")


def insert_causative(node):
    if node.data == "":
        logger.error(f"Skipping node with empty data: {node}")
        return
    msg_text = f'For obstacle "{node.data}" produce a list of contributing factors in outline format.'
    messages = [{"role": "user", "content": msg_text}]
    model = "gpt-3.5-turbo"
    text = robust_call(model, messages)
    logger.info(msg_text)
    logger.info(text)
    # print("Result:\n",text)
    parse_to_nodes(node.identifier, text, tag="obstacle")

def insert_causative4(node, future_picture):

    if type(node.data) is str:
        obstacle = node.data.rstrip('.')
    elif type(node.data) is dict and len(node.data) == 2:
        obstacle = f'{node.data["title"]}: {node.data["description"]}'
    else:
        print(f"Node should be dict, instead it is: {node.data}")
        sys.exit(1)

    msg_text = f'The future picture "{future_picture}" has an obstacle "{obstacle}". Produce a list of this obstacle\'s contributing factors in json format.'
    logger.info(msg_text)
    # text = robust_call(model, messages)
    text = call_gpt4(msg_text)

    with open(os.path.join(path, "cache4.json"), "w", encoding='utf-8') as f:
        json.dump(utils.cache4, f)

    logger.info(text)
    normalized_data = utils.normalize_data(text)

    # print("Result:\n",text)
    insert_nodes(node.identifier, normalized_data, tag="obstacle")

def save_tree(filename="o.json"):
    j = json.loads(tree.to_json(with_data=True))
    with open(os.path.join(path, filename), "w", encoding='utf-8') as f:
        json.dump(j, f)
    # print(json.dumps(j, indent=2))

def create_nodes4(root_question):
    msg_text = f'Produce a list of obstacles in json format to this future picture goal: "{root_question}".'

    # messages = [{"role": "user", "content": root_question}]
    # model = "gpt-3.5-turbo"
    # text = robust_call(model, messages)
    logger.info(msg_text)
    data = call_gpt4(msg_text)
    logger.info(data)
    # print("Using prefetched text")
    normalized_data = utils.normalize_data(data)
    insert_nodes("root", normalized_data, tag="obstacle")


def main():
    global config
    global path

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        return 1

    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    tree.create_node(data=config["root_node_name"], identifier="root", tag="root")

    # logger.basicConfig(filename=os.path.join(path,'g2o.log'), encoding='utf-8', level=logger.DEBUG)
    log_filename = os.path.join(path, "g2o.log")

    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename=log_filename, maxBytes=0, backupCount=5, encoding="utf-8"
    )
    if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
        # Rotate the log file
        handler.doRollover()

    logger.addHandler(handler)

    try:
        with open(os.path.join(path, "cache4.json"), "r", encoding='utf-8') as f:
            utils.cache4 = json.load(f)
    except (IOError, OSError):
        print("No cache4.json file")
    except (json.JSONDecodeError):
        print("cache4.json file not parsable")

    future_picture = config["future_picture"].rstrip('.')

    # root_question = f'The future picture is "{future_picture}".  What are the obstacles to attaining this desirable future?'
    create_nodes4(future_picture)

    with open(os.path.join(path, "cache4.json"), "w", encoding='utf-8') as f:
        json.dump(utils.cache4, f)

    print_tree("root")

    leaf_list = tree.leaves()
    for n in leaf_list:
        insert_causative4(node=n, future_picture=future_picture)
        print_tree("root")
        # debugging break
        # print("Sleep 2")

        # break

    save_tree()
    return


if __name__ == "__main__":
    sys.exit(main())
