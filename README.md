# AI-Powered Problem Structuring Toolkit

## Overview

This project implements the **GOSR** (Goal ← Obstacles ← Solutions ← Resources) framework to address complex societal challenges — often referred to as "wicked problems" — using a structured, AI-augmented process.

Inspired by systems thinking and grounded in cognitive problem-solving theory, GOSR helps communities map out the path from a future vision to the local resources that can help realize it. It supports stakeholders in building a **shared language**, fostering **collective agency**, and visualizing an actionable roadmap.

### Purpose
This toolkit provides:
- A structured process for turning complex goals into actionable maps.
- Python scripts and prompts for using AI to accelerate initial drafts.
- Tools to visualize and refine solutions and resource mappings.

### Reference Framework
The model is rooted in:
- Kells, K. (2019). [*A Proposed Practical Problem-Solving Framework...*](https://arxiv.org/abs/1911.13155)
- Kells, K. (2020). [*A Technology-Assisted Social Computing Framework for Solving Complex Social Problems.*](https://www.humancomputation.com/2020/papers.html)

---

## How AI Accelerates This Framework

In traditional settings, the GOSR process takes 3–6 months via stakeholder meetings. AI allows rapid prototyping:

| Step                 | With AI                      | Time                |
|----------------------|------------------------------|---------------------|
| Define Goal (G)      | Human or AI-assisted draft   | 15 min              |
| List Obstacles (O)   | AI suggestion of ~10 themes  | 30 min              |
| Subdivide Obstacles  | AI generates 100 sub-parts   | 30 min              |
| Map Solutions (S)    | AI brainstorms 1,000 ideas   | 12 hours (½ day)    |
| Suggest Resources (R)| AI identifies 1K–5K resources| 120 hours (5 days)  |

---

## Project Structure

```
ai/
├── scripts/
│   ├── main/        # Core GOSR pipeline
│   ├── convert/     # Export to DOCX, mind map, Google Maps
│   ├── utils/       # URL cleaning, validation
│   └── lib/         # Shared Python modules
├── requirements.txt
├── README.md
```

---

## Example Workflow

1. **Create a project directory** under `projects/` and add a `config.yaml`:

```yaml
future_picture: "Reduce loneliness in New York City"
root_node_name: "Un-Lonely NYC"
root_question: "What are the obstacles to reducing loneliness in New York City?"
locality: "New York"
country: "USA"
major_theme_obstacles:
  - "Urban anonymity"
  - "High cost of living"
  - "Digital dependency"
```

2. **Activate your Python environment:**

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. **Run the GOSR scripts:**

```sh
python scripts/main/g2o.py projects/unlonely-nyc/
python scripts/main/o2s.py projects/unlonely-nyc/
python scripts/main/s2r.py projects/unlonely-nyc/
```

4. **Clean and export data:**

```sh
python scripts/utils/raw2resources.py projects/unlonely-nyc/
python scripts/convert/json2doc.py projects/unlonely-nyc/ --stage r
python scripts/convert/json2mm.py projects/unlonely-nyc/ --stage s
```

---

## Script Reference

To help you automate each stage of the GOSR workflow and manage your outputs, this section documents the main scripts, their purpose, and usage.

### Core GOSR Scripts (scripts/main)

1. **g2o.py**  
   - Purpose: AI-assisted generation of Obstacles from your defined Goal.  
   - Usage:
     ```sh
     python scripts/main/g2o.py <project_dir> [--model MODEL] [--output obstacles.json]
     ```
   - Outputs: `obstacles.json` in the project directory.

2. **o2s.py**  
   - Purpose: AI-assisted brainstorming of Solutions for each obstacle.  
   - Usage:
     ```sh
     python scripts/main/o2s.py <project_dir> [--model MODEL] [--output solutions.json]
     ```
   - Inputs: `obstacles.json`  
   - Outputs: `solutions.json`

3. **s2r.py**  
   - Purpose: AI-assisted discovery and mapping of Resources to each solution.  
   - Usage:
     ```sh
     python scripts/main/s2r.py <project_dir> [--model MODEL] [--output resources_raw.json]
     ```
   - Inputs: `solutions.json`  
   - Outputs: `resources_raw.json`

### Utility Scripts (scripts/utils)

1. **raw2resources.py**  
   - Purpose: Clean and normalize the raw resource output into a structured `resources.json`.  
   - Usage:
     ```sh
     python scripts/utils/raw2resources.py <project_dir>
     ```
   - Inputs: `resources_raw.json`  
   - Outputs: `resources.json`

2. **recheck_resource_urls.py**  
   - Purpose: Validate and fix broken URLs in `resources.json`.  
   - Usage:
     ```sh
     python scripts/utils/recheck_resource_urls.py <project_dir> [--timeout SECONDS]
     ```
   - Inputs/Outputs: `resources.json`

### Conversion & Export Scripts (scripts/convert)

1. **json2doc.py**  
   - Purpose: Export your G/O/S/R data to a Word document.  
   - Usage:
     ```sh
     python scripts/convert/json2doc.py <project_dir> --stage <g|o|s|r> [--format docx]
     ```
   - Example:
     ```sh
     python scripts/convert/json2doc.py projects/unlonely-nyc --stage r
     ```

2. **json2mm.py**  
   - Purpose: Export Solutions (or any stage) as a mind-map (`.mm` format).  
   - Usage:
     ```sh
     python scripts/convert/json2mm.py <project_dir> --stage <g|o|s|r>
     ```

3. **r2google-maps.py**  
   - Purpose: Generate a Google Maps HTML overlay of your resources.  
   - Usage:
     ```sh
     python scripts/convert/r2google-maps.py <project_dir> [--output map.html]
     ```

---

## Example Outputs

- Google Maps with resource overlays:  
  - NYC: https://www.google.com/maps/d/viewer?mid=1jfIz0rAfu2L8w3gEdjKIxq0BfDGMr3E  
  - Nova Scotia: https://www.google.com/maps/d/viewer?mid=1AJY1yIR4D8bH1LMCGz9fKRLSn8mU5fg

- Use Case: Reducing Urban Anonymity  
  - Obstacle: Lack of social cohesion  
  - Solution: Intergenerational activities, community gardens, mentorships  
  - Resource Map: Community centers, NGOs, government programs

---

## Contributing / Future Work

We're actively looking to:
- Build a visualization tool for dynamic GOSR maps
- Improve AI alignment and validation tools
- Support community-run "Backbone Organizations" to maintain models

Contact: [team.earth contact page](https://team.earth/#contact)

---

## License

MIT License
