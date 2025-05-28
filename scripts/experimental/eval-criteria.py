from treelib import Node, Tree
import json
import logging, logging.handlers
import sys
import time
import yaml
import os
from utils import call_gpt4, load_tree, tree
from r_stats import run_stats, r_normalize, get_program_value, get_organization_value
import utils
from datetime import datetime
import random


logger = logging.getLogger()

config = None
path = None

global_resources_list = []

# city = "London"
# country = "England"
max_resource_loops = 1


def next_number(curr_parent):
    for i in range(1, 100):
        trial = ".".join([curr_parent, str(i)])
        if tree.get_node(trial) is None:
            return str(i)


def outline(children, indent=0):
    for c in children:
        if type(c) == str:
            print(f"{indent*'  '}{c}")
        elif type(c) == dict:
            for k, v in c.items():
                print(f"{indent*'  '}{k}")
                outline(v["children"], indent + 2)


def print_tree(identifier, indent=0):
    node = tree.get_node(identifier)
    logger.info(f"> {indent*'  '}> {node.data}")
    for c in tree.children(identifier):
        print_tree(c.identifier, indent + 2)


def save_tree(filename):
    j = json.loads(tree.to_json(with_data=True))
    with open(os.path.join(path, filename), "w", encoding='utf-8') as f:
        json.dump(j, f)
    # print(json.dumps(j, indent=2))


def add_resources(node):
    # msg_text = f"Given this undesired issue: \"{node.tag}\" produce a list of possible solutions the community can contribute to."
    # msg_text = f'Given this undesired issue: "{node.tag}" produce a list of possible solutions the community can contribute to, delineating the Israeli community, the Palestinian and Arab community, and the international community.'
    # messages = [{"role": "user", "content": msg_text}]
    # model = "gpt-3.5-turbo"
    # text = robust_call(model, messages)
    resources_list = get_resources(node)
    index = len(global_resources_list)
    for r in resources_list:
        rr = r_normalize(r)
        rr["id"] = index
        index += 1
        global_resources_list.append(rr)
    node.tag = "solution"
    for r in resources_list:
        r_node = {"id": r["id"]}
        tree.create_node(data=r_node, parent=node, tag="resource")


def get_resources(node):
    global locality, country
    #     text = f"""We want to list the efforts in {city}, {country} that implement this solution:
    # \"{node.data}\"
    # Can you list and describe each effort and then mention the organization implementing it, all in JSON format as a plain list of dicts? Include address, email, and website.
    # """
    text = f"""We want to list existing efforts in {locality}, {country} that implement this solution:
\"{node.data}\"
Can you list and describe each real effort and then mention the organization implementing it, all in JSON format as a plain list of dicts? Include address, email, and valid web page.
"""
    # data = {
    #     "efforts": [
    #         {
    #             "name": "Inclusive Curriculum Initiative",
    #             "description": "An advocacy initiative to push for the integration of educational materials covering the topic of extremism and its impact on communities within the Ottawa-Carleton District School Board (OCDSB). The program aims to prepare students to critically evaluate extremist narratives and understand the importance of diversity and inclusion.",
    #             "organization": "Ottawa-Carleton District School Board (OCDSB)",
    #             "address": "133 Greenbank Road, Ottawa, Ontario K2H 6L3",
    #             "email": "communications@ocdsb.ca",
    #             "website": "https://www.ocdsb.ca/",
    #         },
    #         {
    #             "name": "University Awareness Programs",
    #             "description": "Collaborations between university student associations and faculty to include courses and workshops that address the identification of extremist tactics and their societal impacts. These programs are designed to empower students with the knowledge to engage constructively in diverse communities.",
    #             "organization": "University of Ottawa",
    #             "address": "75 Laurier Ave E, Ottawa, ON K1N 6N5",
    #             "email": "info@uottawa.ca",
    #             "website": "https://www.uottawa.ca/",
    #         },
    #         {
    #             "name": "Community Resilience Fund",
    #             "description": "A fund that supports local projects aimed at countering radicalization to violence. This includes initiatives to improve education on extremist influences through the development of specialized curricula.",
    #             "organization": "Public Safety Canada",
    #             "address": "269 Laurier Avenue West, Ottawa, Ontario K1A 0P8",
    #             "email": "publicsafety.canada@canada.ca",
    #             "website": "https://www.publicsafety.gc.ca/",
    #         },
    #         {
    #             "name": "Youth Empowerment Program",
    #             "description": "A program designed to give young people in Ottawa the tools to understand and respond to extremist messaging. This includes workshops and seminars as part of the school curriculum.",
    #             "organization": "Ottawa Police Service",
    #             "address": "474 Elgin St, Ottawa, ON K2P 2J6",
    #             "email": "community_police@ottawapolice.ca",
    #             "website": "https://www.ottawapolice.ca/",
    #         },
    #     ],
    #     "note": "This is a note",
    # }

    total_data = []
    omit_list = []

    omit_text = ""

    for i in range(0, max_resource_loops):
        data = call_gpt4(text + omit_text)

        if type(data) is list and len(data) > 0:
            logger.info(f"data is list type, converting to dict")
            data = {"wrap_list": data}

        if type(data) is dict:
            # one single resource dict (or error)
            if (
                get_program_value(data) is not None
                and get_organization_value(data) is not None
            ):
                total_data.extend([data])
                break
            elif "status" in data and data["status"] == "error":
                break
            elif (
                len(data.keys()) == 0 or type(data[next(iter(data.keys()))]) is not list
            ):
                logger.warning(f"unknown data value returned: {type(data.values())}")
                break
            for k, v in data.items():
                if type(v) is list:
                    # total_data.extend(next(iter(data.values())))
                    total_data.extend(v)
                elif type(v) is dict:
                    if (
                        get_program_value(v) is not None
                        and get_organization_value(v) is not None
                    ):
                        total_data.extend([v])
                else:
                    logger.info(f"ignoring non-list, non-program dict {k}, {v}")
            omit_list = [d["name"] for d in total_data if "name" in d.keys()]
            omit_text = (
                "Please omit the following, since we already know about them: "
                + ", ".join(omit_list)
            )

    return total_data


def save_resources():
    with open(os.path.join(path, "resources-raw.json"), "w", encoding='utf-8') as f:
        json.dump(global_resources_list, f)


def load_resources():
    global global_resources_list
    file_path = os.path.join(path, "resources.json")
    if os.path.exists(file_path) and os.access(file_path, os.R_OK):
        with open(file_path, "r", encoding='utf-8') as f:
            global_resources_list = json.load(f)

def open_cache(cache_path):
    "Open cache file"
    try:
        with open(cache_path, "r", encoding='utf-8') as f:
            utils.cache4 = json.load(f)
    except (IOError, OSError):
        print(f"No file {cache_path}")
    except json.JSONDecodeError:
        print(f"File not parsable: {cache_path}")

def main():

    outs = [
        {'title': 'Innovation Challenges and Hackathons', 'description': 'Host local challenges or hackathons that incentivize the development of innovative solutions to local policy and regulatory problems affecting technology access.'},
        {'title': 'Tech Access Programs', 'description': 'Developing programs that provide affordable or free technology devices to low-income residents, thus reducing the hardware barrier to digital access.'},
        {'title': 'Innovation Challenges', 'description': 'Organize challenges or hackathons that invite local tech enthusiasts and professionals to develop innovative solutions that are compatible with, or can enhance, existing infrastructure components.'}   ,
        {'title': 'Grant Writing Support', 'description': 'Training interested community members in the art of grant writing to increase the likelihood of obtaining external funding for city projects.'},
        {'title': 'Municipal Bonds for Citizens', 'description': "Issue municipal bonds that allow local citizens to invest directly in the city's infrastructure projects, offering them a financial stake in the city's development."},
        {'title': 'Local Hackathons for Security', 'description': 'Organize hackathons that challenge participants to find vulnerabilities in new technologies and develop solutions, thereby contributing to a safer technological environment.'},
        {'title': 'Expert Volunteer Program', 'description': 'Set up a program where retired government workers or professionals with knowledge of the bureaucratic system volunteer to assist individuals and businesses in dealing with administrative tasks.'}   ,
        {'title': 'Language Exchange Programs', 'description': 'Establish community-driven language exchange programs where Portuguese speakers can learn other languages while teaching Portuguese to non-speakers.'},
        {'title': 'Innovation Hubs and Incubators', 'description': 'Create community-driven innovation hubs and business incubators that encourage entrepreneurship and support new ventures which can positively integrate technology into traditional industries.'},
        {'title': 'Affordable Connectivity', 'description': 'Work with internet service providers to create low-cost broadband plans for low-income households or offer community-sponsored Wi-Fi in underserved areas to reduce the cost barrier for internet access.'},
        {'title': 'Youth Engagement in Tech', 'description': 'Promote STEM (Science, Technology, Engineering, and Math) education at an early age to build a foundation for understanding and embracing technological progress throughout one’s career.'},
        {'title': 'Local Tech Workshops', 'description': 'Organize workshops led by tech industry professionals to provide hands-on training in skills that are in high demand within the tech sector.'},
        {'title': 'Community Innovation Hubs', 'description': 'Establish community innovation hubs where residents can access the latest technology, receive training, and collaborate on tech-focused projects. These hubs could provide internships or project-based learning experiences.'},
        {'title': 'Incentivize Innovation', 'description': 'Local authorities and business associations could offer grants or awards for innovative solutions to interoperability problems, incentivizing the community to work on practical and impactful solutions.'},
        {'title': 'Community Tech Workshops', 'description': 'Organize workshops where community members can come together to learn about and contribute to technological projects. These workshops can also serve as a platform to discuss infrastructure needs and crowdsource innovative solutions.'},
        {'title': 'Inclusive Technology Workshops', 'description': 'Create workshops that educate residents on how to use new technologies, highlighting practical benefits in their daily lives, such as saving time or money.'},
        {'title': 'Local Library Enhancement', 'description': 'Upgrade the technological resources at public libraries in Lisbon to include modern computers, software, and devices. Offering tech literacy courses here can also accommodate additional learning for members of the workforce.'},
        {'title': 'Technology Incubators', 'description': 'Support or create local incubators that can help startups focused on developing technological solutions for infrastructure issues. These startups can provide innovative solutions and fresh perspectives on infrastructure problems.'},
        {'title': 'Annual Lisbon Tech Forum', 'description': 'Host an annual forum for stakeholders to discuss progress, challenges, and the roadmap for technology integration across different sectors in the community.'},
        {'title': 'Community Workshops and Training', 'description': 'Organize educational workshops for local developers, IT professionals, and businesses to learn best practices for ensuring system interoperability. These should cover current standards, open APIs, and system integration techniques.'},
        {'title': 'Technology Recycling Programs', 'description': 'Promote and facilitate the recycling and refurbishing of old technology, which can then be donated or sold at minimal cost to those in need.'},
        {'title': 'Remote Training Opportunities', 'description': 'Make use of online training platforms and e-learning resources to provide accessible training opportunities, especially for those who cannot attend in-person training due to logistical or financial constraints.'},
        {'title': 'Subsidized Internet Programs', 'description': 'Work with local internet service providers to offer subsidized internet access for low-income families to help bridge the digital divide.'},
        {'title': 'Civic Tech Volunteer Corps', 'description': 'Mobilize a pool of tech-savvy volunteers who can assist government bodies in evaluating and implementing tech projects efficiently, minimizing bureaucratic red tape.'},
        {'title': 'Continuous Regulation Reviews', 'description': 'Implement a system for continuous review of regulations affecting the tech industry with the aim of updating and removing unnecessary bureaucratic barriers.'},
        {'title': 'Sustainability and Tech Assessments', 'description': "Facilitate regular sustainability assessments for businesses to evaluate their technology's life span, ROI, and alignment with future industry trends."},
        {'title': 'Outreach and Awareness Campaigns', 'description': 'Initiate awareness campaigns highlighting the importance of tech education and the opportunities it presents, aiming to increase enrollment in related training programs.'},
        {'title': 'Public-Private Partnerships', 'description': 'Encourage partnerships between the public sector, private companies, and NGOs to invest in infrastructure projects. This can lead to shared expertise, resources and risk, as well as provide better technological services for the community.'},
        {'title': 'Youth-Led Tech Initiatives', 'description': 'Encourage youth-led initiatives that focus on peer-to-peer education and technology mentoring for various age groups.'},
        {'title': 'Local IP Policy Advocacy', 'description': 'Encourage and facilitate community engagement with policymakers to advocate for stronger IP protection measures and streamlined IP registration processes.'},
        {'title': 'Mentorship Programs', 'description': 'Establish mentorship programs connecting experienced business mentors with upcoming entrepreneurs to provide guidance and build confidence.'},
        {'title': 'Transparent Technology Adoption Policies', 'description': 'Advocate for municipal policies that require transparency in how new technologies are implemented and how they handle personal data.'},
        {'title': 'Public-Private Partnerships', 'description': 'Establish partnerships between the government, non-profits, and private companies to fund infrastructure improvements and educational initiatives aimed at reducing the digital divide.'},
        {'title': 'Local Advisory Boards', 'description': 'Establish advisory boards with diverse societal representation to guide tech companies in understanding and aligning with local values and priorities.'},
        {'title': 'Startup Competitions and Hackathons', 'description': 'Organize events that bring together entrepreneurs, developers, and investors – with prize money or investment for winning solutions that solve city-specific problems.'},
        {'title': 'Innovation Pilot Programs', 'description': 'Propose and support pilot programs that operate under temporary regulatory relaxations to demonstrate the benefits of innovations.'},
        {'title': 'Success Stories', 'description': 'Share local success stories of businesses or individuals who have benefited from adopting the new technologies to motivate and inspire the workforce.'},
        {'title': 'Digital Literacy in Schools', 'description': 'Integrate digital literacy and basic cybersecurity education into school curriculums to prepare the next generation for the growing complexity of technology in everyday life.'},
        {'title': 'Community Tech Hubs', 'description': 'Establish community-led tech hubs that coordinate resources, share knowledge, and support startups, reducing the need for external funding.'},
        {'title': 'Third-Party Certification Program', 'description': 'Develop a certification program for third-party service providers that certifies their adherence to robust cybersecurity protocols.'},
        {'title': 'Change Champions', 'description': "Identify and empower 'change champions' within the organization who can inspire others and lead by example in the transition to new technologies."},
        {'title': 'Crowdfunding for Infrastructure', 'description': 'Launch crowdfunding campaigns to raise funds for specific technological infrastructure projects within the community. This empowers residents to financially contribute to initiatives that they find crucial for their area.'},
        {'title': 'Volunteer Tech Support Network', 'description': 'Create a network of tech-savvy volunteers who can provide assistance with setting up and maintaining the necessary infrastructure in less advantaged areas, as well as helping to educate residents on usage.'},
        {'title': 'Cultural Sensitivity Training for Tech Workers', 'description': 'Offer training programs for individuals working in the tech sector to increase their awareness and appreciation of local customs and practices, ensuring a respectful integration of technology.'},
        {'title': 'Technology Skill-Building for Entrepreneurs', 'description': 'Support small business owners and budding entrepreneurs by providing specialized technology training and resources that can help them to grow their businesses and remain competitive.'},
        {'title': 'Tech Industry Roundtables', 'description': 'Host roundtable discussions with representatives from the tech industry, government, and civic groups to foster dialogue and address community concerns. By working together, these groups can ensure that technology works for the benefit of the entire city.'},
        {'title': 'Community Crowdfunding for Tech Initiatives', 'description': 'Organize community crowdfunding campaigns to support important technology projects which can improve local infrastructure and services, ensuring continuation even during economic downturns.'},
        {'title': 'Customizable Technology Solutions', 'description': 'Encourage tech companies to develop customizable technology solutions that can be adapted to individual comfort levels and needs, allowing residents to engage with technology at their own pace.'},
        {'title': 'Engagement with Policymakers', 'description': 'Encourage direct dialogue between the tech community and policymakers. Providing a channel for communication can help regulators understand the impact of their decisions and potentially lead to more favorable regulations.'},
        {'title': 'Digital Transformation of Bureaucracy', 'description': 'Promote digital solutions for bureaucratic processes to make them more efficient, reducing paperwork and speeding up the decision-making process.'},
        {'title': 'Local Tech Community Groups', 'description': "Support the formation and growth of tech community groups that provide networking opportunities, share resources, and collaborate on projects that enhance members' technical skills."},
        {'title': 'Educational Outreach', 'description': 'Organize educational outreach programs that teach digital skills and the importance of internet access to residents, while informing them about available resources and solutions.'},
        {'title': 'Expert Consultations', 'description': 'Invite legal and technological experts to provide consultations to the community and regulators, to bridge the gap between the current legal framework and technological advancements.'},
        {'title': 'Tech-for-Good Showcases', 'description': 'Organize events that showcase successful tech projects from other communities and how similar initiatives could positively impact Lisbon, aimed particularly at local decision-makers.'},
        {'title': 'Government Incentives for Training', 'description': 'Lobby for government incentives or subsidies that encourage local businesses to invest in training their employees on new technologies.'},
        {'title': 'Cooperative Compliance Framework', 'description': 'Create a cooperative where tech companies can pool resources to address compliance collectively, benefitting from economies of scale.'},
        {'title': 'Community Workshops and Hackathons', 'description': 'Organize events to engage the tech community in coming up with solutions to regulatory issues and prototype new ideas that comply with or advance current regulations.'},
        {'title': 'Local Tech Idea Incubator', 'description': "Create an incubator program that encourages residents to submit and develop their ideas for technological innovations, which can align with the city's strategic vision."},
        {'title': 'Public-Private Partnership Initiatives', 'description': 'Develop a framework for public-private partnerships (PPPs) that enables joint efforts on projects with societal impact, facilitating collaboration between different stakeholders.'}    ,
        {'title': 'Community Tech Education Programs', 'description': 'Organize local workshops and educational initiatives to raise awareness about the benefits of technology advancements to society and economy, targeting both the general public and politicians.'},
        {'title': 'Career Transition Support', 'description': 'Provide resources and guidance for professionals in other sectors to transition to tech through targeted training initiatives.'},
        {'title': 'Continuing Professional Education', 'description': 'Promote continuous learning and professional development courses in cybersecurity to help current IT professionals upskill and transition into cybersecurity roles.'},
        {'title': 'IP Awareness Campaigns', 'description': 'Launch awareness campaigns highlighting successful collaborative projects in Lisbon that managed to effectively navigate intellectual property challenges, showcasing best practices and encouraging a culture of respect for IP.'},
        {'title': 'Government Incentive Programs', 'description': 'Advocate for local government to introduce incentives, such as tax breaks or grants, to attract more venture capital into the Lisbon tech scene.'},
        {'title': 'Community-Based Tech Education Programs', 'description': 'Organize workshops and training sessions with local universities and tech companies to educate citizens on the basics of technology, cybersecurity, and digital literacy. This can empower the public to better use and understand complex systems and recognize potential security threats.'},
        {'title': 'Affordable Housing Policies', 'description': 'Implement strict affordable housing policies to ensure that real estate development driven by the tech economy does not price out long-time residents, thus preserving economic diversity.'}       ,
        {'title': 'Local Tech Workshops and Bootcamps', 'description': "Encourage the organization of workshops, bootcamps, and short courses focusing on the most in-demand tech skills. Local tech companies and educational institutions could collaborate to deliver these training opportunities, tailored specifically to the industry's needs."},
        {'title': 'Collaborative Pilot Projects', 'description': 'Work with local government to implement pilot projects that operate under special regulatory conditions. The outcomes of these pilots can demonstrate the value of innovation and lead to regulatory adjustments.'},
        {'title': 'Volunteer Expertise Exchange', 'description': 'Create a platform where local professionals can volunteer their skills and expertise to tech startups in exchange for equity, services, or community recognition.'},
        {'title': "Adoption of a 'See Something, Say Something' Policy", 'description': 'Encourage the community to adopt a mindset of vigilance and responsibility where individuals know how and are motivated to report any indicators of insider threats as part of their civic duty.'},
        {'title': 'Startup Liaison', 'description': 'Appoint a liaison officer who works directly with tech startups to understand their challenges with current regulations and represent their interests in the legislative process.'},
        {'title': 'Neighborhood Newsletters', 'description': 'Distribute regular newsletters in local neighborhoods that contain easy-to-understand information on technology and its local impact.'},
        {'title': 'Community-Driven Standards', 'description': 'Work towards developing community-driven standards and best practices for working with and transitioning from legacy systems.'},
        {'title': 'Public-Private Education Initiatives', 'description': 'Encourage collaboration between the public and private sectors to finance and implement educational initiatives that target the needs of the local tech economy.'},
        {'title': 'Local IP Legal Clinics', 'description': 'Set up pro bono legal clinics specializing in intellectual property to offer legal advice and guidance to those in Lisbon facing issues regarding IP rights and disputes.'},
        {'title': 'Crowdsourced IP Watch', 'description': 'Create a community-run platform where individuals can report and discuss potential IP violations, and offer support to those whose rights may have been infringed.'},
        {'title': 'Public-Private Partnerships', 'description': 'Engage in partnerships between the public sector, private companies, and non-profits to pool resources and expertise for the benefit of the community.'},
        {'title': 'Inclusive Multilingual Resources', 'description': 'Ensure that all cybersecurity resources are available in Portuguese and other commonly spoken languages within the community to reach a broader audience.'},
        {'title': 'Small Business Support Programs', 'description': 'Encourage and support the creation and growth of small businesses and startups in traditional sectors, offering them mentorship and guidance on how to integrate technology into their business models.'},
        {'title': 'Partnership Advocacy Groups', 'description': 'Establish or support local advocacy groups focused on the importance of public-private partnerships, which can campaign for better policies, educate the community, and facilitate connections between sectors.'},
        {'title': 'Tech Vision Steering Committee', 'description': 'Establish a diverse committee that can outline key strategic goals for technology adaptation, ensuring a broad range of perspectives and a unified direction for Lisbon.'},
        {'title': 'Community Workshops on Bureaucracy Navigation', 'description': 'Organize local workshops to educate citizens and entrepreneurs on how to effectively navigate the bureaucratic process, which forms to prioritize, and who to contact for specific services.'},
        {'title': 'Cultural Liaison Officers', 'description': 'Appoint cultural liaison officers within key public and private organizations to help bridge the gap between different cultural groups and advocate for inclusive digital service provision.'}       ,
        {'title': 'Partner with Educational Institutions', 'description': 'Collaborate with universities and technical schools to include interoperability in their curriculum, preparing future professionals with the mindset and skills needed to create compatible systems.'},
        {'title': 'Inclusionary Zoning', 'description': 'Mandating a percentage of new construction to be affordable housing, ensuring that as the city grows, it includes homes for people of all income levels.'},
        {'title': 'Education Programs', 'description': 'Develop educational programs in partnership with local schools and universities to cultivate a knowledgeable base of citizens who can provide innovative solutions for integrating new technologies.'}      ,
        {'title': 'Local Government Grants and Incentives', 'description': 'Advocate for local government programs that provide grants, rebates, or tax incentives for businesses started by underrepresented entrepreneurs.'},
        {'title': 'Local Government Partnership', 'description': 'Work with local government officials to create a tech advisory council that can provide input on regulatory processes to make them more startup-friendly.'},
        {'title': 'Mobile Learning Units', 'description': 'Deploy mobile tech education units to teach digital skills in remote or underserved areas where residents might not be able to travel to fixed locations.'},
        {'title': 'Tech Mentorship Network', 'description': 'Develop a network of tech mentors who can provide guidance and support to local businesses and citizens endeavoring to adapt to new technologies.'},
        {'title': 'Educational Outreach', 'description': 'Develop and conduct educational campaigns to increase awareness among policymakers about technological advancements and their potential implications for regulations.'},
        {'title': 'Local Library Digital Literacy Initiatives', 'description': 'Leverage local libraries as resource centers for digital literacy where older adults can access learning materials and attend technology courses.'},
        {'title': 'Pilot Programs and Beta Testing', 'description': 'Start with small-scale pilot programs to test out tech initiatives. Allow community members to be part of the beta testing, offering them a firsthand experience of the benefits and the opportunity to suggest improvements.'},
        {'title': 'Policy Advocacy Groups', 'description': 'Form or join policy advocacy groups that coordinate efforts to propose regulatory changes that could lower compliance costs for tech businesses.'},
        {'title': 'Innovation Workshops', 'description': 'Organize workshops with regulators, technologists, and citizens to find common ground and co-create solutions that comply with regulations while fostering innovation.'},
        {'title': 'Public-Private Partnerships (PPPs)', 'description': 'Foster partnerships between the local government and private entities to finance and manage technology projects efficiently, combining public oversight with private sector expertise and funding.'},
        {'title': 'Liaison Officer Initiative', 'description': 'Designate or elect liaison officers within the tech community tasked with maintaining a productive relationship between tech companies and regulatory authorities.'},
        {'title': 'Promoting Open Source Technologies', 'description': 'Encouraging the use and development of open-source software within Lisbon to reduce dependence on single vendors and enable widespread collaboration.'},
        {'title': 'Community Wi-Fi Extensions', 'description': 'Encourage residents who have access to high-speed internet to share their connection through community Wi-Fi initiatives, extending the service through external antennas or other technologies.'}  ,
        {'title': 'Educational Workshops and Skill Sharing', 'description': 'Conduct free or low-cost educational workshops to improve the tech skills of community members. An upskilled community can contribute more effectively to technology projects and initia,tives.'}
    ]

    "Main functionality"
    # global config, path
    global locality, country, max_resource_loops

    locality = config["locality"]
    country = config["country"]
    max_resource_loops = config.get("max_resource_loops", max_resource_loops)

    cache_path = os.path.join(path, "cache-eval.json")
    open_cache(cache_path)

    in_file = "s.json"
    logger.info("loading existing %s" % in_file)
    load_tree(os.path.join(path, in_file))
    logger.info("loading existing resources")
    load_resources()

    leaf_list = tree.leaves()

    # rs = []
    # for o in outs:
    #     for l in range(0, len(leaf_list)):
    #         if leaf_list[l].data == o:
    #             rs.append(l)
    #             break
    # print(rs)

    random_numbers = {}
    full_set = set(range(0,len(leaf_list)))
    random_numbers = random.sample(range(0,len(leaf_list)+1), 100)
    prior = []
    # prior.extend([1747, 33, 219, 1100, 1843, 303, 257, 943, 1799, 216, 1846, 397, 1616, 315, 559, 1026, 1897, 1999, 141, 1532, 1659, 1772, 1283, 1510, 1643, 1832, 214, 1774, 1511, 706, 1889, 1314, 1593, 1932, 114, 768, 240, 1337, 776, 180, 1495, 1983, 1950, 801, 77, 1000, 735, 1229, 1938, 1483, 763, 874, 1277, 1455, 317, 1781, 769, 1555, 689, 1293, 1076, 1824, 1867, 673, 740, 1615, 1421, 1406, 146, 207, 956, 1031, 883, 749, 1136, 1714, 50, 1437, 599, 1864, 1352, 703, 1872, 1732, 16, 1535, 415, 1813, 746, 266, 1338, 227, 434, 581, 233, 222, 1890, 374, 788, 998])
    # prior.extend([85, 946, 1569, 1925, 1274, 643, 1157, 1347, 1617, 451, 91, 1439, 816, 771, 1008, 567, 512, 1523, 1835, 753, 1581, 1841, 1313, 181, 850, 157, 86, 717, 1825, 1974, 298, 1743, 781, 1605, 225, 923, 1107, 1679, 1126, 518, 1062, 1161, 3, 1540, 1549, 1485, 1377, 1627, 1828, 96, 322, 464, 1928, 929, 1757, 1464, 1633, 1133, 1734, 952, 1315, 824, 1692, 691, 638, 1143, 1804, 1047, 524, 614, 1986, 1988, 1620, 1394, 1770, 226, 297, 140, 1368, 1559, 1029, 129, 901, 1708, 509, 1363, 217, 1450, 1496, 1995, 74, 201, 607, 1025, 1921, 1687, 729, 1349, 1003, 1630])    # random_numbers["A"] = set([741, 284, 1037, 1068, 715, 55, 1070, 529, 737, 300, 470, 336, 848, 478, 859, 222, 994, 850, 1039, 344, 103, 5, 1055, 279, 882, 678, 809, 352, 603, 391, 877, 1003, 913, 331, 31, 123, 791, 11, 888, 919, 642, 618, 430, 421, 923, 285, 25, 895, 312, 185, 828, 429, 1056, 201, 272, 276, 718, 1022, 139, 80, 704, 1, 1058, 428, 236, 699, 347, 620, 950, 59, 371, 122, 657, 802, 540, 307, 299, 105, 670, 242, 14, 98, 633, 426, 783, 504, 12, 644, 589, 434, 550, 510, 1054, 543, 497, 289, 44, 600, 130, 179])
    # prior.extend([1102, 1821, 244, 392, 866, 166, 1332, 1301, 1381, 1541, 1184, 652, 224, 1951, 120, 1870, 371, 58, 62, 1059, 779, 1530, 1664, 896, 809, 980, 751, 958, 1587, 437, 305, 1319, 1169, 381, 168, 69, 398, 338, 1794, 107, 1258, 1180, 1407, 312, 629, 1111, 89, 1562, 1991, 694, 962, 1382, 1428, 1709, 670, 1822, 827, 878, 352, 1151, 113, 1806, 323, 812, 202, 1460, 155, 939, 1765, 1458, 165, 1172, 460, 1524, 885, 1985, 1959, 186, 679, 610, 254, 393, 1634, 963, 382, 899, 886, 1037, 147, 619, 252, 1514, 1533, 984, 584, 1927, 977, 800, 821, 1702])
    # prior.extend([775, 969, 1558, 1218, 1242, 1749, 1876, 156, 1356, 1724, 1858, 1582, 1922, 1884, 1717, 419, 628, 1271, 1414, 1273, 459, 448, 1552, 291, 56, 1018, 482, 1786, 1895, 1011, 1470, 569, 1370, 1564, 1943, 1566, 888, 189, 1859, 80, 1210, 1963, 1220, 55, 505, 1975, 342, 1618, 563, 112, 1478, 1116, 1686, 1446, 1176, 1075, 825, 1491, 586, 1318, 1061, 1121, 1715, 721, 598, 1517, 1119, 1348, 1440, 1647, 1357, 1992, 846, 1354, 857, 160, 725, 1612, 1287, 1057, 1002, 28, 1297, 907, 734, 754, 1454, 1911, 1248, 1944, 690, 1690, 1010, 547, 230, 1967, 1752, 927, 450, 1444])
    # random_numbers["B"] = set([239, 245, 86, 911, 107, 724, 399, 617, 590, 968, 613, 638, 17, 945, 436, 297, 569, 442, 930, 936, 575, 554, 605, 861, 364, 546, 565, 441, 353, 1067, 1025, 329, 7, 792, 983, 917, 891, 694, 490, 752, 892, 438, 154, 264, 238, 57, 476, 323, 1017, 114, 992, 157, 922, 475, 904, 381, 820, 929, 1040, 466, 643, 675, 875, 1077, 688, 811, 548, 1021, 491, 743, 822, 354, 885, 656, 873, 1064, 834, 687, 63, 526, 927, 396, 184, 939, 21, 142, 47, 377, 175, 932, 918, 193, 449, 380, 1016, 509, 536, 946, 155])
    prior.extend([207, 95, 582, 244, 37, 874, 990, 170, 223, 286, 390, 453, 144, 275, 450, 562, 303, 130, 597, 914, 691, 133, 744, 61, 686, 300, 997, 14, 526, 588, 157, 967, 665, 1013, 587, 966, 617, 790, 432, 882, 285, 822, 777, 83, 917, 653, 215, 585, 821, 734, 63, 879, 173, 534, 94, 948, 229, 192, 706, 422, 937, 1011, 23, 354, 114, 837, 65, 338, 624, 270, 566, 164, 87, 15, 75, 222, 351, 9, 245, 812, 944, 332, 635, 132, 598, 719, 90, 154, 986, 716, 159, 186, 623, 66, 304, 276, 1002, 227, 907, 396])
    prior.extend([492, 523, 620, 575, 451, 287, 198, 574, 806, 573, 581, 162, 963, 43, 474, 725, 679, 407, 798, 485, 519, 827, 104, 962, 689, 166, 3, 508, 404, 680, 392, 978, 769, 738, 444, 542, 652, 273, 968, 161, 249, 663, 54, 932, 334, 772, 377, 347, 487, 105, 667, 19, 794, 38, 457, 742, 243, 934, 320, 929, 780, 99, 580, 639, 197, 21, 211, 849, 554, 426, 717, 209, 1008, 312, 1012, 815, 486, 214, 292, 604, 921, 540, 188, 17, 242, 745, 4, 406, 776, 340, 514, 342, 814, 557, 723, 160, 1004, 363, 284, 59])
    prior.extend([957, 50, 622, 139, 855, 324, 854, 871, 903, 120, 877, 732, 674, 935, 741, 532, 76, 804, 1017, 77, 569, 331, 713, 721, 704, 355, 647, 212, 469, 325, 952, 793, 257, 495, 184, 651, 869, 1, 238, 547, 813, 770, 461, 484, 853, 748, 842, 862, 612, 676, 729, 506, 504, 80, 831, 433, 670, 976, 692, 479, 277, 219, 757, 28, 565, 984, 423, 992, 428, 644, 954, 852, 664, 645, 591, 625, 927, 53, 627, 467, 943, 397, 237, 801, 949, 987, 358, 203, 817, 137, 873, 905, 417, 759, 42, 357, 830, 702, 548, 881])
    remaining_set = full_set - set(prior)
    # random_numbers["D"] = set([120, 967, 1051, 580, 198, 567, 615, 99, 1074, 468, 451, 261, 693, 195, 934, 915, 501, 810, 664, 799, 926, 853, 137, 765, 164, 408, 225, 461, 677, 707, 777, 243, 388, 41, 340, 513, 931, 368, 425, 374, 547, 863, 730, 742, 778, 988, 998, 24, 411, 545, 61, 970, 874, 471, 458, 36, 92, 803, 1073, 221, 727, 611, 180, 127, 1027, 112, 1052, 74, 389, 419, 700, 409, 854, 54, 1053, 631, 158, 332, 849, 835, 653, 954, 947, 845, 37, 709, 477, 912, 681, 78, 551, 812, 1059, 253, 424, 701, 277, 410, 52, 634, 1012, 77, 171, 483, 669, 318, 883, 161, 349, 252, 823, 839, 395, 132, 925, 149, 760, 555, 325, 1079, 415, 403, 636, 651, 1035, 339, 519, 703, 210, 573, 813, 1060, 453, 521, 413, 746, 594, 1005, 83, 302, 126, 966, 1001, 237, 473, 825, 439, 199, 775, 933, 165, 754, 1010, 1063, 472, 544, 842, 485, 763, 655, 614, 101, 581, 562, 719, 35, 93, 738, 973, 535, 731, 949, 817, 202, 133, 867, 150, 73, 736, 465, 674, 786, 311, 520, 104, 234, 1049, 385, 637, 240, 49, 81, 524, 599, 735, 262, 647, 720, 194, 571])
    random_numbers = random.sample(list(remaining_set), 100)

    print(random_numbers)

    for i in random_numbers:
        print(leaf_list[i].data)

    sys.exit(0)

    count = 0
    for l in leaf_list:
        count = count + 1
        print(f"{datetime.now().isoformat()} {count}/{len(leaf_list)} {100*count/len(leaf_list):.3g}%", l.data)
        # add_resources(l)
        # print_tree("root")
        # save_resources()
        # save_tree()
        # with open(cache_path, "w", encoding='utf-8') as f:
        #     json.dump(utils.cache4, f)
        # debugging break
        # break
        # run_stats(global_resources_list)

    # leaf_list = tree.leaves()
    # for n in leaf_list:
    # insert_causative(n)
    # print_tree("root")
    # print("Sleep 30")
    # time.sleep(30)

    # save_tree()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        sys.exit(1)

    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding='utf-8') as file:
        config = yaml.safe_load(file)

    log_filename = os.path.join(path, "s-eval.log")

    logger.setLevel(logging.DEBUG)

    handler = logging.handlers.RotatingFileHandler(
        filename=log_filename, maxBytes=0, backupCount=5, encoding="utf-8"
    )
    if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
        # Rotate the log file
        handler.doRollover()

    logger.addHandler(handler)

    RETVAL = main()

    sys.exit(RETVAL)
