import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import openai
from treelib import Node, Tree
import json
import logging, logging.handlers
import sys
import time
import requests
import yaml
import re
from utils import call_gpt4, parse_to_nodes, load_tree, tree, insert_nodes, setup_openai
import utils
from datetime import datetime

# Use the shared OpenAI setup function
setup_openai()

from utils import setup_logging
setup_logging("o-extract.log", backup_count=5)
logger = logging.getLogger(__name__)

config = None
path = None


def next_number(curr_parent):
    for i in range(1, 100):
        trial = ".".join([curr_parent, str(i)])
        if tree.get_node(trial) is None:
            return str(i)


def outline(children, indent=0):
    for c in children:
        if type(c) == str:
            logger.info(f"{indent*'  '}{c}")
        elif type(c) == dict:
            for k, v in c.items():
                logger.info(f"{indent*'  '}{k}")
                outline(v["children"], indent + 2)


def add_solutions(node):
    msg_text = f'Given this undesired issue in {config["locality"]}, {config["country"]}: "{node.data}", produce a list of potential solutions the community can contribute to, relevant to the local community.'
    messages = [{"role": "user", "content": msg_text}]
    model = "gpt-3.5-turbo"
    text = robust_call(model, messages)
    parse_to_nodes(node.identifier, text, tag="solution")


def add_solutions4(node):
    # msg_text = f'Given this undesired issue: "{node.data}" produce a list in json format of possible solutions the community can contribute to.'
    msg_text = f'Given this undesired issue in {config["locality"]}, {config["country"]}: "{node.data}", produce a list in json format of potential solutions the community can contribute to, relevant to the local community. ' +\
    'Each solution should have the format: {"solution": {"title":"...", "description":"..."}}'
# messages = [{"role": "user", "content": msg_text}]
    # model = "gpt-3.5-turbo"
    logger.info(msg_text)
    text = call_gpt4(msg_text)
    logger.debug(text)
    insert_nodes(node.identifier, text, tag="solution")


def save_tree(filename="s.json"):
    j = json.loads(tree.to_json(with_data=True))
    with open(os.path.join(path, filename), "w", encoding='utf-8') as f:
        json.dump(j, f)
    # print(json.dumps(j, indent=2))


def main():
    global config
    global path

    if len(sys.argv) != 2:
        logger.error(f"Usage: {sys.argv[0]} path")
        return 1

    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    filename = "o.json"
    with open(os.path.join(path, filename), "r", encoding='utf-8') as f:
        j = json.load(f)
        # print(json.dumps(j, indent=2))
    for l in j["root"]["children"]:
        logger.info(l["obstacle"]["data"])

    # load_tree(os.path.join(path, "o.json"))

    # j = json.loads(tree.to_json(with_data=True))
    # with open(os.path.join(path, "debug.json"), "w", encoding='utf-8') as f:
    #     json.dump(j, f)

    # log_filename = os.path.join(path, "o2s.log")

    # logger.setLevel(logging.INFO)
    # handler = logging.handlers.RotatingFileHandler(
    #     filename=log_filename, maxBytes=0, backupCount=5, encoding="utf-8"
    # )
    # if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
    #     # Rotate the log file
    #     handler.doRollover()
    # logger.addHandler(handler)

    # try:
    #     with open(os.path.join(path, "cache4.json"), "r", encoding='utf-8') as f:
    #         utils.cache4 = json.load(f)
    # except (IOError, OSError):
    #     print("No cache4.json file")
    # except (json.JSONDecodeError):
    #     print("cache4.json file not parsable")

    # leaf_list = tree.leaves()

    # with open(os.path.join(path, "cache4.json"), "w", encoding='utf-8') as f:
    #     json.dump(utils.cache4, f)

    # count = 0
    # for l in leaf_list:
    #     add_solutions4(l)
    #     save_tree()
    #     # debugging break
    #     # break
    #     # time.sleep(1)
    #     count += 1
    #     # print(f"{count}/{len(leaf_list)}[{100*count/len(leaf_list):.3g}%]", l.data)
    #     print(f"{datetime.now().isoformat()} {count}/{len(leaf_list)} {100*count/len(leaf_list):.3g}%", l.data)
    #     # break

    #     with open(os.path.join(path, "cache4.json"), "w", encoding='utf-8') as f:
    #         json.dump(utils.cache4, f)

    sys.exit(0)


if __name__ == "__main__":
    sys.exit(main())
