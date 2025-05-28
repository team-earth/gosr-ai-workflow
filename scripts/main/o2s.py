import os
import json
import logging
import logging.handlers
import sys
import yaml
from datetime import datetime

from utils import (
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
    The solutions are inserted as child nodes under the given node.
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

    # Save the initial tree structure for debugging purposes
    # j = json.loads(tree.to_json(with_data=True))
    # with open(os.path.join(path, "debug.json"), "w", encoding='utf-8') as f:
    #     json.dump(j, f)

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
