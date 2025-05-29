"""
o2s.py - Obstacles to Solutions (O2S) Workflow Script

This script automates the process of generating community-driven solutions for
identified obstacles using GPT-4. It loads a tree of obstacles, queries GPT-4
for solutions to each leaf node (obstacle), and saves the results in a structured
JSON format. The workflow is configurable via a YAML file and maintains a cache
to optimize repeated LLM calls.

Main Steps:
1. Load configuration and obstacle tree.
2. For each obstacle (leaf node), generate solutions using GPT-4.
3. Insert solutions into the tree and save progress.
4. Maintain a cache and log progress for reproducibility.

Usage:
    python o2s.py <working_directory_path>
"""

import os
import json
import logging
import logging.handlers
import sys
import yaml
from datetime import datetime

from gosr.lib.utils import (
    call_gpt4,
    load_tree,
    tree,
    insert_nodes,
    setup_openai,
    cache4,
    normalize_data,
)

# Initialize OpenAI API credentials
setup_openai()
logger = logging.getLogger(__name__)

config = None  # Will hold the loaded YAML configuration
path = None    # Will hold the working directory path

def add_solutions4(node):
    """
    Generate and insert solutions for a given obstacle node using GPT-4.

    Args:
        node: A tree node representing an obstacle. The node must have a 'data' attribute.

    Side Effects:
        - Calls GPT-4 to generate solutions.
        - Inserts solutions as child nodes under the given node.
        - May limit the number of solutions based on config.
    """
    global config
    if config is None:
        raise ValueError("Configuration not loaded. 'config' is None.")
    msg_text = (
        f'Given this undesired issue in {config["locality"]}, {config["country"]}: "{node.data}", '
        'produce a list in json format of potential solutions the community can contribute to, relevant to the local community. '
        'Each solution should have the format: {"solution": {"title":"...", "description":"..."}}'
    )
    logger.info(msg_text)
    text = call_gpt4(msg_text)
    logger.debug(text)
    # Normalize and limit the number of solutions if needed
    normalized_data = normalize_data(text)
    max_items = config.get("max_items_per_llm_call", None)
    if max_items is not None and isinstance(normalized_data, list):
        normalized_data = normalized_data[:max_items]
    insert_nodes(node.identifier, normalized_data, tag="solution")

def save_tree(filename="s.json"):
    """
    Save the current tree structure to a JSON file.

    Args:
        filename (str): The name of the file to save the tree to (default: 's.json').

    Raises:
        ValueError: If the working directory path is not set.
    """
    global path
    if path is None:
        raise ValueError("Path is not set. Please set the working directory path before saving the tree.")
    # Convert the tree to a JSON-serializable object
    j = json.loads(tree.to_json(with_data=True))
    # Write the tree to disk using UTF-8 encoding
    with open(os.path.join(path, filename), "w", encoding='utf-8') as f:
        json.dump(j, f)

def main():
    """
    Main entry point for the O2S (Obstacles to Solutions) workflow.

    Loads configuration, tree, and cache, then generates solutions for each leaf node.
    Saves progress and cache after each node is processed.

    Returns:
        int: Exit code (0 for success, 1 for usage error).
    """
    global config
    global path

    # Ensure the script is called with the correct number of arguments
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        return 1

    # Set the working directory path from the command-line argument
    path = sys.argv[1]

    # Load configuration from config.yaml
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    # Load the obstacle tree from o.json
    load_tree(os.path.join(path, "o.json"))

    # Set up a rotating file handler for logging
    log_filename = os.path.join(path, "o2s.log")
    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        filename=log_filename, maxBytes=0, backupCount=5, encoding="utf-8"
    )
    # Rotate the log file if it already exists and is not empty
    if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
        handler.doRollover()
    logger.addHandler(handler)

    # Try to load the cache from disk if it exists
    try:
        with open(os.path.join(path, "cache4.json"), "r", encoding='utf-8') as f:
            cache4.update(json.load(f))
    except (IOError, OSError):
        print("No cache4.json file")
    except json.JSONDecodeError:
        print("cache4.json file not parsable")

    # Get all leaf nodes (obstacles) in the tree
    leaf_list = tree.leaves()

    # Save the cache after loading (to ensure it's up to date)
    with open(os.path.join(path, "cache4.json"), "w", encoding='utf-8') as f:
        json.dump(cache4, f)

    count = 0
    # For each leaf node (obstacle), generate and insert solutions
    for l in leaf_list:
        add_solutions4(l)  # Generate and insert solutions for this obstacle
        save_tree()        # Save the updated tree after each insertion
        count += 1
        # Print progress with timestamp, count, and percentage complete
        print(f"{datetime.now().isoformat()} {count}/{len(leaf_list)} {100*count/len(leaf_list):.3g}%", l.data)
        # Save the cache after each node is processed
        with open(os.path.join(path, "cache4.json"), "w", encoding='utf-8') as f:
            json.dump(cache4, f)

    sys.exit(0)

if __name__ == "__main__":
    sys.exit(main())
