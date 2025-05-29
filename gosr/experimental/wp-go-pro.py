# import openai
# from treelib import Node, Tree
import json
# import codecs
import re
import sys
# import time
# from html import escape
import os
import yaml
# import csv

class SlashEscapingEncoder(json.JSONEncoder):
    def encode(self, o):
        result = super(SlashEscapingEncoder, self).encode(o)
        return result.replace('/', '+')
    def iterencode(self, o, _one_shot=False):
        for chunk in super(SlashEscapingEncoder, self).iterencode(o, _one_shot=_one_shot):
            yield chunk.replace('/', '\\/')

def remove_map_non_map_1_categories(kc_map):
    m = kc_map["categories"].copy()
    m = [c for c in m if c["map_id"] in ["1"]]
    kc_map["categories"] = m
    return kc_map

def remove_dicts_with_map_id_1(data):
    if isinstance(data, dict):
        return {k: remove_dicts_with_map_id_1(v) for k, v in data.items() if not (isinstance(v, dict) and v.get('map_id') == '1')}
    elif isinstance(data, list):
        return [remove_dicts_with_map_id_1(item) for item in data if not (isinstance(item, dict) and item.get('map_id') == '1')]
    else:
        return data

def move_dicts_with_map_id_1_to_2(data):
    if isinstance(data, list):
        for item in data:
            move_dicts_with_map_id_1_to_2(item)
    elif isinstance(data, dict):
        if data.get("map_id") == "1":
            data["map_id"] = "2"
        elif data.get("id") == "1":
            data["id"] = "2"
        for key in data:
            move_dicts_with_map_id_1_to_2(data[key])
    return data

def remove_new_custom_fields(kc_map):
    m = kc_map["customfields"].copy()
    m = [c for c in m if int(c["id"]) < 14]
    kc_map["customfields"] = m

def set_polygons_to_empty_list(data):
    if isinstance(data, dict) and 'polygons' in data:
        data['polygons'] = []
    return data

def keep_just_map_2(data):
    filtered_maps = [item for item in data["maps"] if item.get("id") == "1"]
    # Updating the dictionary
    data["maps"] = filtered_maps
    return data

def keep_just_first_markers(data):
    # if "markers" in data and len(data["markers"]) > 0:
    #     data["markers"] = data["markers"][0:10]
    return data

def keep_just_valid_lat_long(data):
    valid_markers = [item for item in data["markers"] if item.get("lat") != "0" and item.get("lng") != "0"]
    # Updating the dictionary
    data["markers"] = valid_markers
    return data

def find_dicts_with_key(node, results = {}):
    """
    Recursively search for dictionaries containing the target key within a nested structure of dictionaries and lists.
    
    Args:
    data (dict or list): The nested data structure to search.
    target_key (str): The key to search for in the dictionaries.
    
    Returns:
    list: A list of dictionaries containing the target key.
    """

    if isinstance(node, dict):
        if "solution" in node:
            if "data" in node["solution"]:
                if "kc360-10" in node["solution"]["data"]:
                    kc360_10 = node["solution"]["data"]["kc360-10"]
                    results[kc360_10] = []
                    for r in node["solution"].get("children", []):
                        results[kc360_10].append(r["resource"]["data"]["id"])

        for value in node.values():
            results = find_dicts_with_key(value, results)
    elif isinstance(node, list):
        for item in node:
            results = find_dicts_with_key(item, results)

    return results

def in_markers_set_icons(data):

    category_to_icon = {
        "A": "icon.png"
    }

    default_icon = "{\"url\":\"//kccommongood.org/wp-content/uploads/2023/08/kccg_pin_shadow.png\",\"retina\":false}"

    for marker in data["markers"]:
        category = marker.get("category")
        if category in category_to_icon:
            marker["icon"] = category_to_icon["category"]
        else:
            marker["icon"] = default_icon

category_map = {}
marker_list = {}

def append_categories(kc_map, categories):
    global category_map

    # id_max = 0
    # for category in kc_map["categories"]:
    #     id_val = int(category.get("id",0))
    #     if id_val > id_max:
    #         id_max = id_val

    id_max = 999

    id_val = id_max + 1
    for c in categories:
        category_map[c] = id_val
        id_val += 1

    for k, v in category_map.items():
        category = {
            "id": str(v),
            "active": "0",
            "category_name": k,
            "category_icon": "",
            "retina": "0",
            "parent": "0",
            "priority": "0",
            "image": "",
            "map_id": "2"
        }
        kc_map["categories"].append(category)


def set_markers_from_resources(kc_map, resources, resource_map):
    global marker_list

    # if "markers" in kc_map and len(kc_map["markers"]) > 0:
    #     kc_map["markers"] = [kc_map["markers"][0]]

    append_categories(kc_map, resource_map.keys())

    counter = 1000
    for k, v in resource_map.items():
        for i in v:
            r = resources[i]
            if "dup" in r:
                dup = r["dup"]
                r = [d for d in resources if d.get("id") == dup][0]
            key = r["address"] + "|" + r["organization"]
            m = {}
            if key in marker_list:
                m = marker_list[key]
                cat_vals = re.split(r'[,\s]+', m["category"])
                cat_int_vals = set([int(v) for v in cat_vals if v])
                cat_int_vals.add(category_map[k])
                cat_vals = map(str, cat_int_vals)
                m["category"] =', '.join(cat_vals)
            else:
                counter += 1
                m = {
                    "id": str(counter),
                    "map_id": "2",
                    "address": r["address"],
                    "description": r["description"],
                    "pic": "",
                    "link": r["website"] if r.get("url_valid", True) else "",
                    "icon": "{\"url\":\"\/\/kccommongood.org\/wp-content\/uploads\/2023\/08\/kccg_pin_shadow.png\",\"retina\":false}",
                    # "lat": "39.1003675",
                    # "lng": "-94.5778788",
                    "anim": "0",
                    "title": r["program"],
                    "infoopen": "0",
                    "category": str(category_map[k]),
                    "approved": "1",
                    "retina": "1",
                    "type": "0",
                    "did": "",
                    "sticky": "0",
                    # "other_data": "a:2:{s:10:\"hover_icon\";s:78:\"\/\/kccommongood.org\/wp-content\/plugins\/wp-google-maps\/images\/spotlight-poi3.png\";s:12:\"hover_retina\";s:1:\"0\";}",
                    "layergroup": "99",
                    "custom_fields_data": [
                        {
                            "id": 15,
                            "name": "organization",
                            "value": r["organization"]
                        },
                        {
                            "id": 7,
                            "name": "360 Focus",
                            "value": k
                        },
                        {
                            "id": 2,
                            "name": "Email",
                            "value": r["email"]
                        }
                    ]
                }
                marker_list[key] = m
                kc_map["markers"].append(m)
    return kc_map

def label_resources(resources, model):
    r = find_dicts_with_key(model)
    return r

def main():
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} path')
        return 1

    path = sys.argv[1]

    # with open(os.path.join(path,'config.yaml'), 'r', encoding='utf-8') as file:
    #     config = yaml.safe_load(file)

    with open(os.path.join(path, "resources.json"), "r", encoding='utf-8') as f:
        resources = json.load(f)
    
    with open(os.path.join(path, "r.json"), "r", encoding='utf-8') as f:
        model = json.load(f)

    resource_map = label_resources(resources, model)

    kc_map_input_file = os.path.join("Export", "kccommongood.wpgooglemaps-1.json")

    wp_go_maps_dir = "WP_GO_MAPS"
    os.makedirs(os.path.join(path,wp_go_maps_dir), exist_ok=True)
    kc_map_output_file = os.path.join(wp_go_maps_dir, "kccommongood.wpgooglemaps.json")

    with open(os.path.join(path,kc_map_input_file), 'r', encoding='utf-8') as in_file:
        kc_map = json.load(in_file)

    kc_map = remove_map_non_map_1_categories(kc_map)
    remove_new_custom_fields(kc_map)
    kc_map = keep_just_map_2(kc_map)

    # kc_map = remove_dicts_with_map_id_1(kc_map)
    kc_map = move_dicts_with_map_id_1_to_2(kc_map)

    # kc_map = set_polygons_to_empty_list(kc_map)
    kc_map = keep_just_valid_lat_long(kc_map)
    # kc_map = keep_just_first_markers(kc_map)
    in_markers_set_icons(kc_map)

    kc_map = set_markers_from_resources(kc_map, resources, resource_map)

    with open(os.path.join(path,kc_map_output_file), "w",
              newline='\n', encoding='utf-8') as out_file:
        json.dump(kc_map, out_file, indent=4, cls=SlashEscapingEncoder)
    return 0

if __name__ == '__main__':
    sys.exit(main())
