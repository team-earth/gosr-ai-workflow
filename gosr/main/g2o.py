"""
g2o.py

GOSR Workflow Phase: Goal → Obstacles

This script takes a single, user-defined Goal and generates a structured list of Obstacles
that may prevent achieving that goal. It is the first step in the GOSR (Goal-Obstacles-Solutions-Resources) pipeline.

Typical usage:
    python g2o.py <config-directory>

Inputs:
    - A directory containing a config.yaml file with the required parameters.

Outputs:
    - A structured JSON file listing obstacles related to the goal.

Reference: See the GOSR process at
https://docs.google.com/presentation/d/1wLkb61LRHV_3o0JqQnr0yeqTPRzzKiLhw0elX2_o6M8/edit?slide=id.g1ff3a93b48e_0_5
"""

"""
Configuration (config.yaml)
---------------------------
The following parameters are required in config.yaml for g2o.py:

- future_picture (str): 
    The main goal or vision statement to analyze.
    This is the central objective for which obstacles will be generated.

- root_node_name (str): 
    The label for the root node in the tree (usually the goal itself).
    This will be used as the root node's name in the obstacle tree structure.

- root_question (str): 
    A prompt or question to initiate obstacle generation.
    This is sent to the language model to generate the initial list of obstacles.

- locality (str): 
    The city, region, or locality for context.
    This provides local context to the language model for more relevant obstacles.

- country (str): 
    The country for context.
    This further contextualizes the goal and obstacles for the language model.

The following parameter is optional:
- major_theme_obstacles (list of str): 
    Known obstacles from the local community, included in the prompt for context if present.
    If provided, these are shared with the language model to inform or refine its generated list of obstacles.

Example config.yaml:
--------------------
future_picture: "Increase community access to healthy food"
root_node_name: "Access to Healthy Food"
root_question: "What are the main obstacles to increasing community access to healthy food?"
locality: "Springfield"
country: "USA"
major_theme_obstacles:
  - "Lack of grocery stores"
  - "Limited public transportation"
  - "High food prices"
"""

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import openai
from treelib.tree import Tree
from treelib.node import Node
import json
import logging
import logging.handlers
import sys
import time
import requests
import yaml
import re
from utils import (
    tree, call_gpt4, insert_nodes, setup_openai, setup_logging,
    normalize_data, cache4
)

# Use the shared OpenAI setup function
setup_openai()

logger = logging.getLogger(__name__)

config = None
path = None

def print_tree(identifier, indent=0):
    """
    Output to stdout the tree starting at node with given identifier.

    Args:
        identifier (str): The node identifier to start printing from.
        indent (int): The indentation level for pretty-printing.
    """
    node = tree.get_node(identifier)
    if node is None:
        logger.warning(f"Node with identifier '{identifier}' not found in tree.")
        return
    logger.info("> %s%s. %s %s", indent*'  ', node.identifier, node.tag, node.data)
    for c in tree.children(identifier):
        print_tree(c.identifier, indent + 2)


# def create_nodes():
#     """
#     Generate and insert obstacles for the root node using the root question from config.
#     """
#     if config is None:
#         raise RuntimeError("Config is not loaded. Make sure to load config before calling create_nodes().")
#     root_question = config["root_question"]
#     messages = [{"role": "user", "content": root_question}]
#     model = "gpt-3.5-turbo"
#     # Call the LLM to get obstacles for the root question
#     text = call_gpt4(root_question)
#     logger.info(root_question)
#     logger.info(text)
#     # Parse the returned text and insert nodes into the tree
#     parse_to_nodes("root", text, tag="obstacle")


def insert_causative4(node, future_picture):
    """
    For a given node and future picture, find and insert contributing factors as sub-nodes.

    Args:
        node: The tree node to expand.
        future_picture (str): The main goal or vision statement.
    """
    # Determine the obstacle description for the prompt
    if isinstance(node.data, str):
        obstacle = node.data.rstrip(".")
    elif isinstance(node.data, dict) and len(node.data) == 2:
        obstacle = f'{node.data["title"]}: {node.data["description"]}'
    else:
        print(f"Node should be dict, instead it is: {node.data}")
        sys.exit(1)

    # Compose the prompt for the LLM to get contributing factors
    msg_text = (
        f'The future picture "{future_picture}" has an obstacle "{obstacle}".\n\n'
        'Produce a list of this obstacle\'s contributing factors or sub-obstacles.\n\n'
        'Create a JSON list of dicts where each sub-obstacle dict has key "title" and "description".'
    )
    logger.info(msg_text)
    # Call the LLM to get contributing factors
    text = call_gpt4(msg_text)

    # Save the cache after each call to persist results
    assert isinstance(path, str) and path, "path must be a non-empty string"
    with open(os.path.join(path, "cache4.json"), "w", encoding="utf-8") as f:
        json.dump(cache4, f)

    logger.info(text)
    # Normalize the returned data and insert as sub-nodes
    normalized_data = normalize_data(text)
    assert config is not None, "Config must be loaded before using it."
    max_items = config.get("max_items_per_llm_call", None)
    if max_items is not None and isinstance(normalized_data, list):
        normalized_data = normalized_data[:max_items]
    insert_nodes(node.identifier, normalized_data, tag="obstacle")


def save_tree(filename="o.json"):
    """
    Write the current tree structure to a JSON file.

    Args:
        filename (str): The output filename (default: "o.json").
    """
    # Convert the tree to a JSON-serializable object
    j = json.loads(tree.to_json(with_data=True))
    # Ensure path is a string before joining
    assert isinstance(path, str) and path, "path must be a non-empty string"
    # Write the JSON to the specified file in the working path
    with open(os.path.join(path, filename), "w", encoding="utf-8") as f:
        json.dump(j, f)


def create_nodes4(root_question):
    """
    Discover and insert the main-theme obstacles to the given future picture statement.

    Args:
        root_question (str): The main question or goal statement.
    """
    global config
    assert config is not None, "Config must be loaded before calling create_nodes4."
    # Compose the prompt for the LLM, including locality and country
    msg_text = (
        f'Produce a list of obstacles specific to {config["locality"]}, {config["country"]}, to this future picture goal: '
        f'"{root_question}"\n\n'
    )
    # Optionally add the major_theme_obstacles line if present in config
    if "major_theme_obstacles" in config and config["major_theme_obstacles"]:
        msg_text += (
            f'Keep in mind the local community\'s own assessment of the same, which consists of these obstacles: {config["major_theme_obstacles"]}.\n\n'
        )
    # Always append the instruction for the JSON format
    msg_text += (
        'Return a JSON list of dicts, with each dict having key "title" and "description".'
    )

    logger.info(msg_text)
    # Call the LLM to get obstacles
    data = call_gpt4(msg_text)
    logger.info(data)
    # Normalize and insert the obstacles into the tree
    normalized_data = normalize_data(data)
    assert config is not None, "Config must be loaded before using it."
    max_items = config.get("max_items_per_llm_call", None)
    if max_items is not None and isinstance(normalized_data, list):
        normalized_data = normalized_data[:max_items]
    insert_nodes("root", normalized_data, tag="obstacle")


def main():
    """
    Main entry point for the GOSR Goal→Obstacles workflow.

    Loads configuration, sets up logging, initializes the tree, loads cache,
    generates obstacles, and saves the resulting tree structure.
    """
    global config
    global path

    # Ensure the script is called with the correct number of arguments
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        return 1

    # Set the working path from the command-line argument
    path = sys.argv[1]
    # Load configuration from config.yaml
    with open(os.path.join(path, "config.yaml"), "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # Create the root node in the tree using the configured root node name
    tree.create_node(data=config["root_node_name"], identifier="root", tag="root")

    log_filename = os.path.join(path, "g2o.log")

    # Set logger level to INFO for this run
    logger.setLevel(logging.INFO)

    # Remove any existing handlers before adding new ones
    logger.handlers.clear()

    # Set up a rotating file handler for logging
    handler = logging.handlers.RotatingFileHandler(
        filename=log_filename, maxBytes=0, backupCount=5, encoding="utf-8"
    )
    # Rotate the log file if it already exists and is not empty
    if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
        handler.doRollover()

    # Add the file handler to the logger
    logger.addHandler(handler)

    # Try to load the cache from disk if it exists
    try:
        with open(os.path.join(path, "cache4.json"), "r", encoding="utf-8") as f:
            cache4.update(json.load(f))
    except (IOError, OSError):
        print("No cache4.json file")
    except json.JSONDecodeError:
        print("cache4.json file not parsable")

    # Prepare the future picture statement (goal) for obstacle generation
    future_picture = config["future_picture"].rstrip(".")

    # Generate and insert the main-theme obstacles
    create_nodes4(future_picture)

    # Save the updated cache to disk
    with open(os.path.join(path, "cache4.json"), "w", encoding="utf-8") as f:
        json.dump(cache4, f)

    # Print the tree structure after initial obstacle insertion
    print_tree("root")

    # For each leaf node (obstacle), generate and insert contributing factors
    leaf_list = tree.leaves()
    for n in leaf_list:
        insert_causative4(node=n, future_picture=future_picture)
        print_tree("root")
        # Uncomment the next line for debugging or to pause between insertions
        # print("Sleep 2")
        # break

    # Save the final tree structure to disk
    save_tree()
    return 0


if __name__ == "__main__":
    # Run the main workflow and exit with its return code
    sys.exit(main())
