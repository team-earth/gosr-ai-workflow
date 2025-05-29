"""
Script: s2r.py
--------------

Purpose:
    This script automates the process of generating and collecting real-world resources (programs, organizations, efforts)
    that implement solutions for obstacles in a community or system, as defined in a hierarchical tree structure.
    It uses OpenAI's GPT-4 to suggest resources for each solution node, normalizes and stores the results, and
    outputs them in structured JSON files for further analysis or visualization.

Workflow:
    1. Loads configuration from a YAML file in the specified project subdirectory (containing locality, country, etc.).
    2. Loads an existing solution tree (s.json) and any cached LLM results.
    3. For each solution node (leaf), queries GPT-4 for real-world efforts implementing that solution in the given locality/country.
    4. Normalizes, deduplicates, and stores the resources in both the tree and a flat resource list.
    5. Saves updated resources and tree structure to disk after each node is processed.
    6. Optionally runs statistics and analysis on the collected resources.

Usage:
    python s2r.py <project_subdirectory>
    - <project_subdirectory> should contain config.yaml, s.json, and will receive s2r.log, resources-raw.json, etc.

Outputs:
    - s2r.log: Log file with progress and errors, written to the project subdirectory.
    - resources-raw.json: Flat list of all collected resources.
    - r.json: Updated tree structure with resource nodes.
    - cache4.json: Cache of LLM responses to avoid redundant API calls.

Configuration (config.yaml):
    - locality: Name of the city or region for context.
    - country: Name of the country for context.
    - max_items_per_llm_call: (Optional) Limit on number of resources per LLM call.
    - max_resource_loops: (Optional) Number of LLM attempts per solution node.

Dependencies:
    - Python 3.x
    - treelib
    - openai
    - pyyaml
    - requests
    - dotenv (optional, for API keys)

See the project README and PowerPoint for more details on the G-O-S-R method and workflow.
"""

import json
import logging
import logging.handlers
import sys
import yaml
import os
from gosr.lib.utils import call_gpt4, load_tree, tree, setup_openai
from gosr.lib.r_stats import run_stats, r_normalize, get_program_value, get_organization_value
import gosr.lib.utils as utils
from datetime import datetime

# Set up the logger for this script
logger = logging.getLogger(__name__)

# Global variables for configuration, path, and resource tracking
config = None
path = None
global_resources_list = []
max_resource_loops = 1  # Default number of LLM attempts per solution node

def next_number(curr_parent):
    """
    Find the next available child number for a given parent node in the tree.
    Used for generating unique node identifiers.
    """
    for i in range(1, 100):
        trial = ".".join([curr_parent, str(i)])
        if tree.get_node(trial) is None:
            return str(i)

def outline(children, indent=0):
    """
    Print a simple outline of the tree structure for debugging or visualization.
    """
    for c in children:
        if type(c) == str:
            print(f"{indent*'  '}{c}")
        elif type(c) == dict:
            for k, v in c.items():
                print(f"{indent*'  '}{k}")
                outline(v["children"], indent + 2)

def print_tree(identifier, indent=0):
    """
    Recursively print the tree starting from the given node identifier.
    """
    node = tree.get_node(identifier)
    if node is not None:
        logger.info(f"> {indent*'  '}> {node.data}")
        for c in tree.children(identifier):
            print_tree(c.identifier, indent + 2)
    else:
        logger.warning(f"Node with identifier '{identifier}' not found.")

def save_tree(filename="r.json"):
    """
    Save the current tree structure to a JSON file in the project directory.
    """
    j = json.loads(tree.to_json(with_data=True))
    if path is None:
        raise ValueError("The variable 'path' must be set to a valid directory string before calling save_tree.")
    with open(os.path.join(path, filename), "w", encoding='utf-8') as f:
        json.dump(j, f)

def add_resources(node):
    """
    For a given solution node, query the LLM for real-world resources,
    normalize and store them, and add them as child nodes in the tree.
    """
    resources_list = get_resources(node)
    # Limit the number of resources if specified in config
    max_items = config.get("max_items_per_llm_call", None) if config is not None else None
    if max_items is not None and isinstance(resources_list, list):
        resources_list = resources_list[:max_items]
    index = len(global_resources_list)
    # Normalize and assign unique IDs to each resource, then add to global list
    for r in resources_list:
        rr = r_normalize(r)
        rr["id"] = index
        index += 1
        global_resources_list.append(rr)
    # Mark the node as a solution node
    node.tag = "solution"
    # Add each resource as a child node in the tree
    for r in resources_list:
        r_node = {"id": r["id"]}
        tree.create_node(data=r_node, parent=node, tag="resource")

def get_resources(node):
    """
    Query the LLM for real-world efforts that implement the given solution node.
    Handles normalization and deduplication of results.
    """
    global locality, country
    # Compose the prompt for the LLM, asking for real-world efforts for this solution
    text = f"""We want to list existing efforts in {locality}, {country} that implement this solution:
\"{node.data}\"
Can you list and describe each real effort and then mention the organization implementing it, all in JSON format as a plain list of dicts? Include address, email, and valid web page.
"""

    total_data = []  # Will accumulate all found resources
    omit_list = []   # Track already found resources to avoid duplicates
    omit_text = ""   # Text to tell the LLM what to omit

    # Try up to max_resource_loops times to get new resources from the LLM
    for i in range(0, max_resource_loops):
        data = call_gpt4(text + omit_text)

        # If the LLM returns a list, wrap it in a dict for consistency
        if type(data) is list and len(data) > 0:
            logger.info(f"data is list type, converting to dict")
            data = {"wrap_list": data}

        if type(data) is dict:
            # If the dict is a single resource, add it and stop
            if (
                get_program_value(data) is not None
                and get_organization_value(data) is not None
            ):
                total_data.extend([data])
                break
            # If the dict signals an error, stop
            elif "status" in data and data["status"] == "error":
                break
            # If the dict is empty or not a list, log and stop
            elif (
                len(data.keys()) == 0 or type(data[next(iter(data.keys()))]) is not list
            ):
                logger.warning(f"unknown data value returned: {data}")
                break
            # Otherwise, process each key/value in the dict
            for k, v in data.items():
                if isinstance(v, list):
                    # If value is a list, add all items to total_data
                    total_data.extend(v)
                elif isinstance(v, dict):
                    # If value is a dict, check if it's a valid resource and add
                    if get_program_value(v) is not None and get_organization_value(v) is not None:
                        total_data.append(v)
                    else:
                        logger.warning(f"dict value for key '{k}' does not have expected structure: {v}")
                else:
                    logger.info(f"ignoring non-list, non-dict value for key '{k}': {v}")
            # Prepare omit_text to avoid duplicates in subsequent LLM calls
            omit_list = [d["name"] for d in total_data if "name" in d.keys()]
            omit_text = (
                "Please omit the following, since we already know about them: "
                + ", ".join(omit_list)
            )

    return total_data

def save_resources():
    """
    Save the flat list of all collected resources to resources-raw.json.
    """
    if path is None:
        raise ValueError("The variable 'path' must be set to a valid directory string before calling save_resources.")
    with open(os.path.join(path, "resources-raw.json"), "w", encoding='utf-8') as f:
        json.dump(global_resources_list, f)

def load_resources():
    """
    Load existing resources from resources.json if present.
    Allows incremental runs without losing previous results.
    """
    global global_resources_list
    if path is None:
        raise ValueError("The variable 'path' must be set to a valid directory string before calling load_resources.")
    file_path = os.path.join(path, "resources.json")
    if os.path.exists(file_path) and os.access(file_path, os.R_OK):
        with open(file_path, "r", encoding='utf-8') as f:
            global_resources_list = json.load(f)

def main():
    """
    Main entry point for the script.
    Loads configuration, sets up logging and OpenAI, loads the tree and cache,
    processes each solution node, and saves results.
    """
    global config, path
    global locality, country, max_resource_loops

    # Check for correct usage
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        return 1

    # Set the working directory path and load config
    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    # --- Logging setup ---
    log_filename = os.path.join(path, "s2r.log")
    logger.handlers.clear()  # Remove any existing handlers

    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(
        filename=log_filename, maxBytes=0, backupCount=5, encoding="utf-8"
    )
    if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
        handler.doRollover()
    logger.addHandler(handler)
    # Optional: also log to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    # --- End logging setup ---

    # --- OpenAI setup ---
    setup_openai()
    # --- End OpenAI setup ---

    # Load locality/country and resource loop settings from config
    locality = config["locality"]
    country = config["country"]
    max_resource_loops = config.get("max_resource_loops", max_resource_loops)

    # Load LLM cache if present
    try:
        with open(os.path.join(path, "cache4.json"), "r", encoding='utf-8') as f:
            utils.cache4 = json.load(f)
    except (IOError, OSError):
        print("No cache4.json file")
    except json.JSONDecodeError:
        print("cache4.json file not parsable")

    # Load the solution tree and any existing resources
    load_tree(os.path.join(path, "s.json"))
    logger.info("loading existing resources")
    load_resources()

    # Get all leaf nodes (solutions) in the tree
    leaf_list = tree.leaves()
    count = 0
    # For each solution node, query for resources, update tree and resource list, and save progress
    for l in leaf_list:
        count = count + 1
        print(f"{datetime.now().isoformat()} {count}/{len(leaf_list)} {100*count/len(leaf_list):.3g}%", l.data)
        add_resources(l)
        save_resources()
        save_tree()
        # Save the LLM cache after each node
        with open(os.path.join(path, "cache4.json"), "w", encoding='utf-8') as f:
            json.dump(utils.cache4, f)
        # Optionally run statistics on the collected resources
        run_stats(global_resources_list)

    # Save the final tree structure
    save_tree()

if __name__ == "__main__":
    # Start the script
    sys.exit(main())
