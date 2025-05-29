import openai
from treelib import Node, Tree
import json

# import codecs
# import re
import sys
import time
from html import escape
import logging, logging.handlers
import os
import yaml

logger = logging.getLogger("r_stats")
logger.setLevel(logging.DEBUG)


def open_json(filename):
    with open(filename, "r", encoding='utf-8') as f:
        j = json.load(f)
    return j


def write_node(n, indent=0):
    s = ""

    if type(n) == dict:
        for k, v in n.items():
            s += f'{"  "*indent}<node TEXT="{escape(k)}">\n'
            for c in v["children"]:
                s += write_node(c, indent + 2)
            s += f'{"  "*indent}</node>\n'
    elif type(n) == str:
        s += f'{"  "*indent}<node TEXT="{escape(n)}"></node>\n'

    return s


def write_tree(d, filename):
    s = ""
    s += '<map version="1.0.1">\n'
    s += write_node(d)
    s += "</map>\n"
    with open(filename, "w", encoding='utf-8') as f:
        f.write(s)


def get_program_value(d):
    possible_keys = [
        "name",
        "Name",
        "program_name",
        "program",
        "event_name",
        "title",
        "Effort Name",
        "Effort",
        "effort_name",
        "project_name",
    ]
    for key in possible_keys:
        if key in d:
            return d[key]
    logger.error(f"Only keys found were {d.keys()}, no program key found among {possible_keys}")
    return None


def get_organization_value(d):
    possible_keys = ["organization"]
    for key in possible_keys:
        if key in d:
            if type(d[key]) is dict:
                return d[key]["name"]
            else:
                return d[key]
    logger.error(f"No organization key found in {d}")
    return None

def r_normalize(r):
    logger.info(f'r_normalize found {type(r)}')
    return r


def run_stats(j):
    # print(j)
    orgs = {}
    programs = {}
    for i in j:
        program = get_program_value(i)
        organization = get_organization_value(i)
        if program in programs:
            logger.warning(
                f"Program: {program}\nOriginal:\t{programs[program]}\nDuplicate:\t{i}"
            )
        else:
            programs[program] = i
            if organization in orgs:
                logger.warning(
                    f"Organization: {organization}\nOriginal:\t{orgs[organization]}\nDuplicate:\t{i}"
                )
            else:
                orgs[organization] = i

    for org in orgs.keys():
        logger.info(f"org: {org}")

    print(
        "Total input:",
        len(j),
        "Unique programs:",
        len(programs),
        "Unique orgs:",
        len(orgs),
    )

def run_urls(j):
    total = 0
    no_url_valid = 0
    true_url_valid = 0
    false_url_valid = 0
    base_url_valid = 0

    for r in j:
        if "dup" in r:
            continue

        total += 1
        if "url_valid" not in r:
            no_url_valid += 1
            # logger.debug(f'{r["id"]}: no_url_valid: {r["website"]}')
        elif r["url_valid"] == True:
            true_url_valid += 1
            # logger.debug(f'{r["id"]}: true_url_valid: {r["website"]}')
        elif r["url_valid"] == False:
            false_url_valid += 1
            logger.debug(f'{r["id"]}: false_url_valid: {r["website"]}')
        else:
            base_url_valid += 1
            # logger.debug(f'{r["id"]}: base_url_valid: {r["url_valid"]} {r["website"]}')

    print(
        "Total resources:", total,
        "no_url_valid:", no_url_valid,
        "true_url_valid:", true_url_valid,
        "false_url_valid:", false_url_valid,
        "base_url_valid:", base_url_valid,
    )

counts = {}
def run_json_counts(j):
    global counts
    for k, v in j.items():
        if k not in counts:
            counts[k] = 1
        else:
            counts[k] += 1
        if k == "obstacle" and type(v) is dict and "children" in v and "solution" in v["children"][0]:
            if "leaf_obstacles" not in counts:
                counts["leaf_obstacles"] = 1
            else:
                counts["leaf_obstacles"] += 1
        if type(v) is dict:
            run_json_counts(v)
        if k == "children":
            for c in j[k]:
                run_json_counts(c)

def main():
    global config
    global path
    global counts

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        return 1

    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    log_filename = os.path.join(path, "r_stats.log")

    handler = logging.handlers.RotatingFileHandler(
        filename=log_filename, maxBytes=0, backupCount=5
    )
    if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
        # Rotate the log file
        handler.doRollover()

    logger.addHandler(handler)

    input_filename = "resources.json"

    j = open_json(filename=os.path.join(path, input_filename))
    logger.info(json.dumps(j, indent=2))
    run_stats(j)
    # run_urls(j)

    input_filename = "r.json"
    with open(os.path.join(path, input_filename), "r", encoding='utf-8') as f:
        j = json.load(f)

    run_json_counts(j)
    for k,v in counts.items():
        print(k,v)

if __name__ == "__main__":
    sys.exit(main())
