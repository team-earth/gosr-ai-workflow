import openai
from openai import OpenAI
import os
from treelib.node import Node
from treelib.tree import Tree
import json
import logging
import logging.handlers
import sys
import time
import requests
import re
import hashlib

def setup_openai():
    """
    Initialize OpenAI API credentials from environment variables.
    Loads .env if available, checks for required variables, and sets them for the OpenAI client.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    api_key = os.getenv("OPENAI_API_KEY")
    org = os.getenv("OPENAI_ORG")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")
    if not org:
        raise ValueError("OPENAI_ORG environment variable not set.")
    openai.api_key = api_key
    openai.organization = org
    global client
    client = OpenAI(api_key=api_key, organization=org)

def setup_logging(log_file="run.log", backup_count=5, level=logging.INFO):
    """
    Set up logging with both file and console handlers.
    Rotates the log file at the start of each run if it exists and is not empty.
    Ensures that logs are written to both a file and the console for visibility.
    """
    try:
        handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=0, backupCount=backup_count, encoding="utf-8"
        )
        if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
            handler.doRollover()
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[handler, logging.StreamHandler()]
        )
    except Exception as e:
        print(f"Logging setup failed: {e}")
        logging.basicConfig(level=level)

logger = logging.getLogger(__name__)
config = None
path = None
cache4 = {}

# Initialize a tree structure to store hierarchical data
tree = Tree()

def next_number(curr_parent_name):
    """
    Generate the next available child number for a given parent node in the tree.
    Returns the next unused integer as a string.
    """
    for i in range(1, 100):
        trial = f"{curr_parent_name}.{i}"
        if tree.get_node(trial) is None:
            return str(i)
    raise RuntimeError("Exceeded maximum child nodes (100) for parent.")

def dehyphenate(text):
    """
    Placeholder for dehyphenating text. Currently returns the input unchanged.
    """
    return text

# Lists of possible keys for titles and descriptions in data dictionaries
title_keys = [
    "obstacle", "Factor", "factor", "solution_title", "strategy", "approach",
    "title", "solution", "name", "      title", "     title", "action",
    "WrappedTextarea-title", "solutionTitle"
]

description_keys = [
    "description", "Description", "solution_description", "details",
    "      description", "detail", "Details", "solutionDescription", "explanation"
]

# Keys that may indicate contributing factors in data
contributing_factors = [
    "obstacle", "contributing_factors", "Contributing Factors", "Contributing_Factors"
]

def get_title_and_description_keys(d):
    """
    Given a dictionary, attempt to identify which keys correspond to the title and description.
    Returns a tuple (title_key, description_key).
    Logs warnings or errors if keys are missing.
    """
    description_reconciliation_keys = {"detail", "details"}
    id_keys = {"solution_id", "id"}
    title_key = None
    description_key = None
    id_key = None
    for k in d:
        k_stripped = k.strip()
        if k_stripped in title_keys:
            if title_key is None:
                title_key = k
        elif k_stripped in description_keys:
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
        logger.warning(f"No title_key or id_key in {list(d.keys())}")
    if description_key is None:
        logger.error(f"No description_key in {list(d.keys())}")
    return title_key, description_key

def normalize_dict(data):
    """
    Normalize a dictionary to a standard format with 'title' and 'description' keys.
    Handles various possible key names and structures.
    Returns a single normalized dict or a list of such dicts.
    """
    # Unwrap if data is like {'solution': {...}}
    if isinstance(data, dict) and len(data) == 1:
        only_value = next(iter(data.values()))
        if isinstance(only_value, dict):
            data = only_value

    # Now proceed as before, looking for title/description
    title_key = None
    description_key = None
    for k in data:
        if "title" in k.lower():
            title_key = k
        if "description" in k.lower():
            description_key = k

    if title_key is None or description_key is None:
        raise ValueError("Missing title or description key in data: {}".format(data))

    title_value = data[title_key]
    description_value = data[description_key]
    if isinstance(title_value, str):
        title_value = title_value.replace('_', ' ')
    else:
        title_value = str(title_value)
    return {
        "title": title_value,
        "description": description_value
    }

def normalize_list(data):
    """
    Normalize a list of dictionaries, applying normalize_dict to each element.
    Returns a list of normalized dicts.
    """
    return [normalize_dict(d) for d in data if isinstance(d, dict)]

def normalize_data(data):
    """
    Recursively normalize data, which may be a list, dict, or other type.
    Returns normalized data in a standard format.
    """
    if isinstance(data, list):
        return normalize_list(data)
    if isinstance(data, dict):
        if len(data) == 1:
            key = next(iter(data))
            return normalize_data(data[key])
        return normalize_dict(data)
    return data

def get_obstacle_list(data):
    """
    Extract a list of obstacles from data, handling various possible structures.
    Returns a list of obstacle dicts, or None if not found.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if len(data) == 1:
            key = next(iter(data))
            return get_obstacle_list(data[key])
        if len(data) == 2:
            for k, v in data.items():
                if k not in {'obstacle', 'issue'}:
                    return get_obstacle_list(v)
        return [{"title": k, "description": v} for k, v in data.items()]
    logger.error(f"No obstacle list at {data}")
    return None

def insert_nodes(parent_name, data, tag):
    """
    Insert nodes into the tree under the given parent node, using the provided data.
    Each obstacle is added as a child node with the specified tag.
    """
    parent_node = tree.get_node(parent_name)
    obstacle_list = get_obstacle_list(data)
    logger.info(f"obstacle_list: {obstacle_list}")

    if obstacle_list is None:
        return
    for o in obstacle_list:
        if isinstance(o, dict):
            if len(o) == 1:
                # Single key dict: treat value as data
                key = next(iter(o))
                d = o[key]
            else:
                # Expect both obstacle and description
                d = o

            title_key, description_key = get_title_and_description_keys(d)

            if description_key is None:
                raise ValueError("Missing description key in node data: {}".format(d))

            if title_key is None:
                node_data = d[description_key]
            else:
                node_data = {"title": d[title_key], "description": d[description_key]}

            logger.info(f"new node data: {node_data}")
            tree.create_node(
                data=node_data,
                parent=parent_node,
                tag=tag,
            )

def print_tree(identifier, indent=0):
    """
    Recursively print the tree structure starting from the given node identifier.
    """
    node = tree.get_node(identifier)
    if node is None:
        logger.warning(f"Node with identifier '{identifier}' not found.")
        return
    logger.info(f"> {'  ' * indent}{node.identifier}. {node.data}")
    for c in tree.children(identifier):
        print_tree(c.identifier, indent + 2)

cache_dirty = False

from openai.types.chat import ChatCompletionMessageParam

def call_gpt4(msg_text, use_cache=True):
    """
    Call the OpenAI GPT-4 API with the given message text.
    Uses a cache to avoid redundant API calls.
    Handles retries and error logging.
    Returns the parsed JSON response.
    """
    global cache4, cache_dirty

    # Hash the message text to use as a cache key
    key = hashlib.md5(msg_text.encode()).hexdigest()

    # Return cached response if available
    if use_cache and key in cache4:
        print("* ", end="")
        return cache4[key]

    messages: list[ChatCompletionMessageParam] = [
        {"role": "user", "content": msg_text}
    ]
    model = "gpt-4o"

    for attempts in range(5):
        try:
            logger.debug(f'After one second sending: {messages[0].get("content", "")}')
            time.sleep(1)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"}
            )
            response_text = response.choices[0].message.content
            text = str(response_text).strip()
            logger.debug(f'Response: "{text}"')
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
            requests.exceptions.ReadTimeout,
        ) as e:
            logger.warning(
                f"{type(e).__name__} encountered. New API call attempt in {2 ** attempts} seconds...\n{e}"
            )
            time.sleep(2 ** attempts)
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI API call: {e}")
            break
    return f"No valid response from OpenAI API after 5 attempts!"

def add_children(parent, d):
    """
    Recursively add children nodes to the tree from a nested dictionary structure.
    Handles both dict and string children.
    """
    if "children" in d:
        for c in d["children"]:
            if isinstance(c, dict):
                node_key = next(iter(c))
                n = tree.create_node(node_key, parent=parent, data=c[node_key]["data"])
                add_children(n, c[node_key])
            else:
                tree.create_node(data=c.strip(), parent=parent, tag="obstacle")
    else:
        parent.data = d["data"]

def load_tree(file_path):
    """
    Load a tree structure from a JSON file and populate the global tree object.
    """
    with open(file_path, "r", encoding='utf-8') as f:
        d = json.load(f)

    node_key = next(iter(d))
    n = tree.create_node(
        identifier="ROOT", data=d[node_key]["data"].strip(), tag="goal"
    )
    add_children(n, d[node_key])
    logger.debug(json.dumps(tree.to_dict(with_data=True)))

def save_tree(filename="o.json"):
    """
    Save the current tree structure to a JSON file in the specified path.
    """
    # Fix: Check if path is set and handle exceptions
    if not path:
        raise ValueError("Path is not set for saving the tree.")
    j = json.loads(tree.to_json(with_data=True))
    try:
        with open(os.path.join(path, filename), "w", encoding='utf-8') as f:
            json.dump(j, f)
    except Exception as e:
        logger.error(f"Failed to save tree to {filename}: {e}")
