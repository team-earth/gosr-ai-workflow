data = {
    "obstacle": {
        "children": [
            {
                "obstacle": {
                    "data": {
                        "title": "ResistanceToChange",
                        "description": {
                            "LossOfTraditions": "Residents may fear that the influx of technology and outsiders will erode local culture and traditions.",
                            "DisplacementConcerns": "The tech boom could lead to gentrification, raising living costs and displacing long-time residents.",
                            "DigitalDivide": "Some residents may feel left behind or ill-equipped to engage with new technologies, especially older populations.",
                        },
                    }
                }
            },
            {
                "obstacle": {
                    "data": {
                        "title": "EconomicConcerns",
                        "description": {
                            "JobSecurity": "Long-time residents may worry that the new tech economy will threaten their current jobs, especially in non-tech industries.",
                            "RisingCostsOfLiving": "Increased demand for housing and services due to the tech industry's growth could make Lisbon less affordable.",
                        },
                    }
                }
            },
            {
                "obstacle": {
                    "data": {
                        "title": "SocialImpacts",
                        "description": {
                            "CommunityDisruption": "Rapid changes could disrupt the social fabric and community cohesion among long-time residents.",
                            "Inequality": "Technological advancements could exacerbate socio-economic inequalities if the benefits are unevenly distributed.",
                        },
                    }
                }
            },
            {
                "obstacle": {
                    "data": {
                        "title": "CommunicationGaps",
                        "description": {
                            "InsufficientOutreach": "Lack of effective communication about the benefits of tech integration to long-time residents.",
                            "Misinformation": "Spread of misinformation regarding the impact of technology and new developments on the local community.",
                        },
                    }
                }
            },
            {
                "obstacle": {
                    "data": {
                        "title": "PoliticalAndRegulatoryChallenges",
                        "description": {
                            "LackOfPoliticalWill": "Insufficient leadership or political will to bridge the gap between tech growth and community needs.",
                            "RegulatoryHurdles": "Existing regulations may hinder the adoption of new technologies or the growth of the tech sector.",
                        },
                    }
                }
            },
            {
                "obstacle": {
                    "data": {
                        "title": "EnvironmentalConcerns",
                        "description": {
                            "SustainabilityFears": "Residents might worry that an increase in tech facilities and workers will strain the environment and infrastructure."
                        },
                    }
                }
            },
            {
                "obstacle": {
                    "data": {
                        "title": "CulturalDifferences",
                        "description": {
                            "MisalignmentWithValues": "Tech solutions may not align with the values or lifestyles of long-time residents, leading to resistance."
                        },
                    }
                }
            },
        ],
        "data": {
            "title": "Public Perception",
            "description": "Resistance from long-time residents towards rapid technological changes or gentrification could affect the perception and adoption of improved services.",
        },
    }
}


def xform(o):
    l = {"children": [], "data": o["data"]["title"]}
    for k, v in o["data"]["description"].items():
        e = {"data": {"title": k, "description": v}}
        l["children"].append({"obstacle": e})
    return l


for o in data["obstacle"]["children"]:
    x = xform(o["obstacle"])
    print(x)
