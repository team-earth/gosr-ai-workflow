from utils import setup_openai, setup_logging
setup_openai()
setup_logging("query-by-state.log", backup_count=5)
import logging
logger = logging.getLogger(__name__)

import openai
import os
import json
import csv

# Define the list of states
states = [
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
]

# Query to be asked with state substitution
query_template = """\
As a simple JSON list of dictionaries, give me a comprehensive list of organizers of paid internships for high school and college-age youth, 
that include experiential learning and partnerships with local businesses and organizations. 
Find both large-scale and smaller, local programs, as long as their primary address is in the state of {}. 
Prioritize programs offering high school and college internships, project-based learning, and community engagement.
Find programs that are similar to https://proxsummer.org/, including this one if it exists in this state.

Please include the following fields for each program: 
state, city, street_address, postal_code, program_name, organization_name, website, telephone, program_description, and organization_description. 

Also, evaluate each of these programs in terms of their geographical reach and their orientation towards rural vs. urban settings, 
and include this information in the program description as well as in additional fields geographical_reach and urban_vs_rural_orientation. 
Ensure that programs offering internships in any part of the state are included.

Return only the pure JSON list, without any introductory text, explanations, markdown, or additional formatting."""

# Path to cache file
cache_file = "state_queries_cache.json"

# Load existing cache if it exists
if os.path.exists(cache_file):
    with open(cache_file, "r") as f:
        cache = json.load(f)
else:
    cache = {}

# Function to get response from OpenAI API
def get_response(state):
    chat_completion = openai.ChatCompletion.create(
        messages=[
            {
                "role": "user",
                "content": query_template.format(state),
            }
        ],
        model="gpt-4o-mini"
    )

    return chat_completion.choices[0].message.content.strip()

# Loop through states and get responses
responses = []
for state in states:
    if state not in cache:
        logger.info(f"Querying for {state}...")
        response = get_response(state)
        cache[state] = response
        responses.append({"state": state, "response": response})
    else:
        logger.info(f"Using cached response for {state}...")
        responses.append({"state": state, "response": cache[state]})

# Save updated cache
with open(cache_file, "w") as f:
    json.dump(cache, f)

# Save responses to a JSON file
output_file = "state_responses.json"
response_list = []
for item in responses:
    val = item["response"]
    jval = json.loads(val)
    response_list.extend(jval)
with open(output_file, "w") as f:
    json.dump(response_list, f)

logger.info(f"Responses saved to {output_file}")

csv_file_path = "state_responses.csv"
headers = response_list[0].keys()
with open(csv_file_path, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.DictWriter(file, fieldnames=headers)
    writer.writeheader()
    writer.writerows(response_list)