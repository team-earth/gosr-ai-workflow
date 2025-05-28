from treelib import Tree
import utils
import pytest


def do_parse(text):
    utils.tree = Tree()
    parent_name = "root"
    utils.tree.create_node("test node name", parent_name)
    utils.parse_to_nodes(parent_name, text)
    tree_output = utils.tree.to_dict(sort=False)
    print(tree_output)
    return tree_output


@pytest.mark.parametrize(
    "text, out",
    [
        (
            """1. Disputes over land ownership:
- Conflicting claims to the same territories
- Historical connections and religious significance attached to specific lands
- Different interpretations of historical records and legal agreements

2. Displacement:
- Palestinian displacement during the establishment of the State of Israel in 1948 (known as the Nakba)
- Jewish displacement following the creation of Israel from surrounding Arab countries
- Ongoing disputes over the right of return for Palestinian refugees

1. Political Factors:
   a. Ideological differences:
      - Disagreements on the role of religion in governance and society
   b. Competing factions:
      - Fatah:
        - Emphasizes negotiations and diplomacy with Israel

1. Political Factors:
   a. Competing factions:
      - Fatah:
        - Founded in the 1950s, it is the largest Palestinian political party
        - Dominant within the Palestinian Authority (PA) and the Palestine Liberation Organization (PLO)
        - Emphasizes negotiations and diplomacy with Israel
      - Hamas:
        - Founded in the late 1980s, it is a Palestinian Islamist political and military organization
        - Controls the Gaza Strip and has widespread support among Palestinians
        - Advocates armed resistance against Israeli occupation
   b. Ideological differences:
      - Disagreements on the role of religion in governance and society
      - Divergent views on the means to achieve Palestinian statehood

3. Geographical Factors:
   a. Separation between Gaza Strip and West Bank:
      - Physical separation between Palestinian territories fosters different political dynamics and priorities
      - Limited interactions between leaders and the general population in different areas

4. Socioeconomic Factors:
   a. Frustration over unemployment and poverty:
      - High unemployment rates and economic struggles contribute to internal tensions
      - Unequal distribution of resources and lack of economic opportunities

Note: The order of factors presented in the outline is for organizational purposes and does not imply any prioritization.
""",
            {
                "test node name": {
                    "children": [
                        {
                            "Disputes over land ownership:": {
                                "children": [
                                    "Conflicting claims to the same territories",
                                    "Historical connections and religious significance attached to specific lands",
                                    "Different interpretations of historical records and legal agreements",
                                ]
                            }
                        },
                        {
                            "Displacement:": {
                                "children": [
                                    "Palestinian displacement during the establishment of the State of Israel in 1948 (known as the Nakba)",
                                    "Jewish displacement following the creation of Israel from surrounding Arab countries",
                                    "Ongoing disputes over the right of return for Palestinian refugees",
                                ]
                            }
                        },
                        {
                            "Political Factors:": {
                                "children": [
                                    {
                                        "Ideological differences:": {
                                            "children": [
                                                "Disagreements on the role of religion in governance and society"
                                            ]
                                        }
                                    },
                                    {
                                        "Competing factions:": {
                                            "children": [
                                                {
                                                    "Fatah:": {
                                                        "children": [
                                                            "Emphasizes negotiations and diplomacy with Israel"
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    },
                                ]
                            }
                        },
                        {
                            "Political Factors:": {
                                "children": [
                                    {
                                        "Competing factions:": {
                                            "children": [
                                                {
                                                    "Fatah:": {
                                                        "children": [
                                                            "Founded in the 1950s, it is the largest Palestinian political party",
                                                            "Dominant within the Palestinian Authority (PA) and the Palestine Liberation Organization (PLO)",
                                                            "Emphasizes negotiations and diplomacy with Israel",
                                                        ]
                                                    }
                                                },
                                                {
                                                    "Hamas:": {
                                                        "children": [
                                                            "Founded in the late 1980s, it is a Palestinian Islamist political and military organization",
                                                            "Controls the Gaza Strip and has widespread support among Palestinians",
                                                            "Advocates armed resistance against Israeli occupation",
                                                        ]
                                                    }
                                                },
                                            ]
                                        }
                                    },
                                    {
                                        "Ideological differences:": {
                                            "children": [
                                                "Disagreements on the role of religion in governance and society",
                                                "Divergent views on the means to achieve Palestinian statehood",
                                            ]
                                        }
                                    },
                                ]
                            }
                        },
                        {
                            "Geographical Factors:": {
                                "children": [
                                    {
                                        "Separation between Gaza Strip and West Bank:": {
                                            "children": [
                                                "Physical separation between Palestinian territories fosters different political dynamics and priorities",
                                                "Limited interactions between leaders and the general population in different areas",
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "Socioeconomic Factors:": {
                                "children": [
                                    {
                                        "Frustration over unemployment and poverty:": {
                                            "children": [
                                                "High unemployment rates and economic struggles contribute to internal tensions",
                                                "Unequal distribution of resources and lack of economic opportunities",
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                    ]
                }
            },
        ),
        (
            """I. Lack of social support systems
   A. Limited availability of community organizations or groups that promote social interaction
   B. Absence of community centers or places where people can gather and connect
   C. Inadequate resources for addressing mental health issues or social challenges

II. High levels of social inequality
   A. Discrimination or prejudice based on factors such as race, gender, or socioeconomic status
   B. Limited opportunities for upward mobility or social advancement
   C. Unequal distribution of resources and services, leading to marginalized communities

III. Weak social cohesion
   A. Lack of trust and cooperation among community members
   B. High levels of crime or violence, leading to heightened fear and mistr""",
            {
                "test node name": {
                    "children": [
                        {
                            "Lack of social support systems": {
                                "children": [
                                    "Limited availability of community organizations or groups that promote social interaction",
                                    "Absence of community centers or places where people can gather and connect",
                                    "Inadequate resources for addressing mental health issues or social challenges",
                                ]
                            }
                        },
                        {
                            "High levels of social inequality": {
                                "children": [
                                    "Discrimination or prejudice based on factors such as race, gender, or socioeconomic status",
                                    "Limited opportunities for upward mobility or social advancement",
                                    "Unequal distribution of resources and services, leading to marginalized communities",
                                ]
                            }
                        },
                        {
                            "Weak social cohesion": {
                                "children": [
                                    "Lack of trust and cooperation among community members",
                                    "High levels of crime or violence, leading to heightened fear and mistr",
                                ]
                            }
                        },
                    ]
                }
            },
        ),
    ],
)
def test_parse_to_nodes(text, out):
    assert do_parse(text) == out
