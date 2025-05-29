import logging
from logging.handlers import RotatingFileHandler
import sys, os
import yaml
import json
import time
import hashlib
from fuzzywuzzy import fuzz
import requests
from urllib.parse import urlparse
import socket
import urllib3

from utils import setup_openai
setup_openai()

from utils import setup_logging
setup_logging("dr-ruth.log", backup_count=5)
import logging
logger = logging.getLogger(__name__)

import openai
from openai import OpenAI

client = OpenAI(api_key=openai.api_key, organization=openai.organization)

config = None

# Path to cache file
cache_file = "dr-ruth.json"
cache_dirty = False

# Load existing cache if it exists
if os.path.exists(cache_file):
    with open(cache_file, "r",encoding="utf-8") as f:
        cache4 = json.load(f)
else:
    cache4 = {}

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
    model = "gpt-4o"

    attempts = 0
    while attempts < 5:
        try:
            logger.debug(f'Sending: {messages[0]["content"]}')
            # time.sleep(1)
            response = client.chat.completions.create(model=model,
            messages=messages,
            # request_timeout=120,
            # seed=32768,
            response_format={"type": "json_object"})
            text = response.choices[0].message.content
            logger.info(f'Response: "{str(text).strip()}"')
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

def validate_program(s, p):
    msg_text = f"""\
Verify that this program is real and that the website, address, and phone
are correct. Set any unverifiable value to JSON null.
Add a new field "validity" grading from A through F as to confidence
that this program is real. 
{p}
"""
    
    # If the program does not receive a minimum B grade, replace the entire
    # program with a valid program given these keywords: {','.join(s['topics'])} and this description 
    # of the context: "{s['description']}" and perform the same validation before
    # return it as JSON.
    logging.debug(msg_text)
    response = call_gpt4(msg_text)
    logging.debug(response)
    return(response)

def find_programs(s):
    msg_text = f"""\
Find a list of real, existing programs in New York State or New York City that implement what 
Dr. Ruth describes as follows:
"{s['description']}", 
generally guided by the keywords {', '.join(s['topics'])}. Generate formatted JSON code as a 
list of dicts, where each dict has the fields:
program_name, program_description, organization, organization_description,
website, address, phone. Find about a dozen real, existing programs. Avoid creating fictional or imaginary ones.
These must be real and operate anywhere in New York State, including NYC and any counties and cities of upstate New York.
"""
    
    # If the program does not receive a minimum B grade, replace the entire
    # program with a valid program given these keywords: {','.join(s['topics'])} and this description 
    # of the context: "{s['description']}" and perform the same validation before
    # return it as JSON.
    logging.debug(msg_text)
    response = call_gpt4(msg_text)
    logging.debug(response)
    return(response)

def validate_resources(path, data):
    global cache4, cache_dirty

    for s in data:
        for i,p in enumerate(s["programs"]):
            s["programs"][i] = validate_program(s,p)
            if cache_dirty:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache4, f)

    with open(os.path.join(path,"resources.json"), "w", encoding="utf-8") as f:
        json.dump(new_data, f)

def debug_programs(programs):
    print(programs)
    print("Data issue")
    sys.exit(1)

def process_program(p, strict):
    EXPECTED_KEYS = [
        "program_name", "program_description", "organization_name", "organization_description",
        "address", "phone", "website"
    ]

    CORRECTED_KEYS = {
        "program": "program_name",
        "organization": "organization_name"
    }
    if not isinstance(p, dict):
        print(p,"Is not dict")
    
    for key in list(p.keys()):
        if key not in EXPECTED_KEYS:
            if strict or key not in CORRECTED_KEYS.keys():
                print(f"unexpected key: {key}")
            else:
                p[CORRECTED_KEYS[key]] = p.pop(key)
    return p

def fix_programs(program_list, strict=False):
    if not isinstance(program_list, list):
        debug_programs(program_list)

    for i,p in enumerate(program_list):
        new_p = process_program(p, strict)
        program_list[i] = new_p

def process_programs(programs):
    """Validate and store"""
    if not isinstance(programs, dict):
        debug_programs(programs)
    if len(programs) != 1:
        debug_programs(programs)


    program_list = next(iter(programs.values()))
    if not isinstance(program_list, list):
        debug_programs(programs)

    fix_programs(program_list)
    fix_programs(program_list, strict=True)

    return program_list

def find_resources(path, data):
    global cache4, cache_dirty

    for s in data:
        programs = find_programs(s)
        program_list = process_programs(programs)
        s["programs"] = program_list
        if cache_dirty:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache4, f)
                cache_dirty = False

def create_resources(s_list):
    s_id = 1
    p_id = 1
    solns = []
    programs = {}
    for s in s_list:
        soln = s.copy()
        soln["programs"] = []
        for p in s["programs"]:
            programs[p_id] = p.copy()
            programs[p_id]["solutions"] = []
            soln["programs"].append(p_id)
            soln["id"] = s_id
            programs[p_id]["solutions"].append(s_id)
            p_id += 1
        s_id += 1
        solns.append(soln)
    
    return solns, programs

def clean_orgs(programs):
    org_map = {
        "Brooklyn Community Services": "Brooklyn Community Services (BCS)",
        "Buffalo Love and Relationship Institute": "Buffalo Love & Relationship Institute",
        "Buffalo Relationship Institute": "Buffalo Love & Relationship Institute",
        "Community Counseling & Mediation": "Community Counseling & Mediation (CCM)",
        "Community Counseling and Mediation": "Community Counseling and Mediation (CCM)",
        "Community Service Society of New York": "Community Service Society of New York (CSS)",
        "Compassionate Friends": "Compassionate Friends NYC",
        "Family Services of Westchester": "Family Services of Westchester, Inc.",
        "Gilda’s Club NYC": "Gilda's Club NYC",
        "Gilda’s Club New York City": "Gilda's Club New York City",        "Buffalo Love & Relationship Institute": "Buffalo Relationship Institute",
        "God’s Love We Deliver": "God's Love We Deliver",    
        "Jewish Board of Family & Children Services": "Jewish Board of Family and Children's Services",
        "Jewish Board of Family & Children's Services": "Jewish Board of Family and Children's Services",
        "Jewish Board of Family & Children’s Services": "Jewish Board of Family and Children's Services",
        "Jewish Board of Family and Children Services": "Jewish Board of Family and Children's Services",
        "Jewish Board of Family and Children's Services": "Jewish Board of Family and Children's Services",
        "Jewish Board of Family and Children’s Services": "Jewish Board of Family and Children's Services",
        "Jewish Community Center of Greater Rochester": "Jewish Community Center (JCC) of Greater Rochester",
        "Meals on Wheels Programs & Services of Rockland": "Meals on Wheels Programs & Services of Rockland, Inc.",
        "Meals on Wheels of Syracuse": "Meals on Wheels of Syracuse, NY",
        "Mental Health America of Dutchess County": "Mental Health America of Dutchess County (MHA DC)",
        "Mental Health Association in New York State (MHANYS)": "Mental Health Association in New York State, Inc. (MHANYS)",
        "Mental Health Association in New York State Inc.": "Mental Health Association in New York State, Inc. (MHANYS)",
        "Mental Health Association in New York State": "Mental Health Association in New York State, Inc. (MHANYS)",
        "Mental Health Association in New York State, Inc. (MHANYS)": "Mental Health Association in New York State, Inc. (MHANYS)",
        "Mental Health Association in New York State, Inc.": "Mental Health Association in New York State, Inc. (MHANYS)",
        "MindfulNYU": "Mindful NYU",
        "NY Socials": "NYC Social",
        "NYC Social": "NY Socials",
        "National Alliance on Mental Illness (NAMI) NYC": "National Alliance on Mental Illness of NYC (NAMI-NYC Metro)",
        "National Alliance on Mental Illness (NAMI-NYC Metro)": "National Alliance on Mental Illness of NYC (NAMI-NYC Metro)",
        "New York State Office of Children & Family Services (OCFS)": "New York State Office of Children & Family Services",
        "New York State Office of Children & Family Services": "New York State Office of Children & Family Services (OCFS)",
        "New York State Office of Children and Family Services (OCFS)": "New York State Office of Children & Family Services",
        "New York State Office of Children and Family Services": "New York State Office of Children & Family Services",
        "NewYork-Presbyterian Hospital": "New York-Presbyterian Hospital",
        "Selfhelp Community Services": "Selfhelp Community Services, Inc.",
        "SingleStop USA": "Single Stop USA",
        "Visiting Neighbors Inc.": "Visiting Neighbors, Inc.",
        }
    for id, p in programs.items():
        if p["organization_name"] in org_map.keys():
            print(f'substituting {p["organization_name"]} --> {org_map[p["organization_name"]]}')
            p["organization_name"] = org_map[p["organization_name"]]
        if p["organization_name"].replace("The ", "") in org_map.keys():
            print(f'substituting {p["organization_name"]} --> {org_map[p["organization_name"].replace("The ","")]}')
            p["organization_name"] = org_map[p["organization_name"].replace("The ","")]

def check_website(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0'

    }

    try:
        # First, try checking the specific URL
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=2)
        if response.status_code == 200:
            # print('200 original', url)
            return url
        else:
            # If the specific page is not found, check the root URL
            root_url = "{uri.scheme}://{uri.netloc}/".format(uri=urlparse(url))

            # if root_url in good_urls and root_url == good_urls[root_url]:
            #     print('previously good base', root_url, url)
            #     return root_url

            response = requests.head(root_url, headers=headers, allow_redirects=True, timeout=2)
            if response.status_code == 200:
                # print('200 base', root_url, url)
                return root_url
            else:
                print(url, 'failed retry, code', response)
                return None
    except requests.RequestException as e:
        print(url, 'request exception', e)
        return None
    # except requests.exceptions.ConnectionError as e:
    #     print('requests.exceptions.ConnectionError', e, url)
    #     return None
    # except (
    #     urllib3.exceptions.NameResolutionError,
    #     urllib3.exceptions.MaxRetryError,
    #     OSError,
    #     requests.exceptions.RequestException,
    #     requests.exceptions.ConnectionError,
    #     socket.gaierror,
    # ) as e:
    #     print("General exception", e, url)
    #     return None


def clean_urls(programs):
    for id, p in programs.items():
        url = p["website"]
        check_website(url)



def dedupe_programs(solns, programs):
    threshold = 95
    dupes = {}
    cnt = 0
    print()
    for id1, p1 in programs.items():
        for id2, p2 in programs.items():
            field = "organization_name"
            c1 = p1[field].replace("The ", "").replace("New York City", "NYC").replace(" and "," & ")
            c2 = p2[field].replace("The ", "").replace("New York City", "NYC").replace(" and "," & ")
            if c1 != c2 and fuzz.ratio(c1, c2) >= threshold:
                if c1+c2 not in dupes.keys():
                    print(f'"{p1[field]}": "{p2[field]}",')
                    dupes[c1+c2] = True
                    cnt += 1
    print(f"Dedupes count: {cnt}")

def write_resources(path, solns, programs):
    
    with open(os.path.join(path,"programs.json"), "w", encoding='utf-8') as f:
        json.dump(programs, f)
    with open(os.path.join(path,"solutions.json"), "w", encoding='utf-8') as f:
        json.dump(solns, f)


def analyze_resources(data):
    ch_count = 0
    section_count = 0
    total_count = 0
    curr_chapter = None
    curr_section = None
    for w in data:
        if curr_chapter is None or curr_chapter != w['chapter']:
            section_count = 0
            ch_count += 1
            curr_chapter = w['chapter']
        if curr_section is None or curr_section != w['section']:
            section_count += 1
            curr_section = w['section']
        total_count += 1
        print(f"{total_count} {ch_count}. {w['chapter']}, {section_count}. {w['section']}, {len(w['programs'])} resources")

def main(path):
    """Main function to execute the program logic."""
    filename = "resources-raw.json"
    
    with open(os.path.join(path,filename), 'r', encoding="utf-8") as file:
        data = json.load(file)

    # analyze_resources(data)
    # new_data = validate_resources(path,data)
    find_resources(path,data)
    solns, programs = create_resources(data)
    # clean_urls(programs)
    clean_orgs(programs)
    dedupe_programs(solns, programs)
    write_resources(path, solns, programs)
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        sys.exit(1)

    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    RETVAL = main(path)
    sys.exit(RETVAL)
