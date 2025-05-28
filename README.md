# AI Problem Structuring

## GOSR Workflow Overview

This project implements the **GOSR** (Goal → Obstacles → Solutions → Resources) workflow for structured problem-solving and resource mapping.  
Each phase is handled by a dedicated script in the `scripts/main/` directory:

- **g2o.py**: Converts a Goal into a structured list of Obstacles.
- **o2s.py**: Converts Obstacles into Solutions.
- **s2r.py**: Maps Solutions to Resources.

### Workflow Steps

1. **Goal**: Define your main objective or vision.
2. **Obstacles**: Identify what stands in the way of achieving the goal.
3. **Solutions**: Brainstorm or generate ways to overcome each obstacle.
4. **Resources**: Find or suggest resources that can help implement each solution.

---

## Project Structure

```
ai/
├── scripts/
│   ├── main/        # Main workflow scripts (core pipeline)
│   │   ├── g2o.py
│   │   ├── o2s.py
│   │   └── s2r.py
│   ├── convert/     # Conversion/export scripts (for docs, maps, etc.)
│   │   ├── json2doc.py
│   │   ├── json2mm.py
│   │   ├── json2map.py
│   │   └── r2google-maps.py
│   ├── utils/       # Standalone utility/cleaning scripts
│   │   └── recheck_resource_urls.py
│   └── lib/         # Shared libraries/modules
│       └── utils.py
├── requirements.txt
├── README.md
└── ...
```

- **main/**: Core GOSR workflow scripts.
- **convert/**: Scripts for exporting/converting data (e.g., to DOCX, mind maps, Google Maps CSV).
- **utils/**: Standalone utility scripts (e.g., data cleaning, validation).
- **lib/**: Shared Python modules (imported by other scripts).

---

## Configuration & Parameterization

The workflow is configured using a `config.yaml` file, which must be present in your project directory (e.g., in `projects/your-project/`).  
This file defines the context and parameters for your run.

### Required Parameters

- **future_picture**:  
  The main goal or vision statement you want to achieve.

- **root_node_name**:  
  The label for the root node in the problem tree (usually the goal itself).

- **root_question**:  
  A prompt or question that will be used to generate obstacles for the goal.

- **locality**:  
  The city, region, or locality for context.

- **country**:  
  The country for context.

- **major_theme_obstacles**:  
  A list of known obstacles from the local community, included in the prompt for additional context.

---

## Example Configuration (`config.yaml`)

Place a file named `config.yaml` in your project directory with content like:

```yaml
future_picture: "Increase community access to healthy food"
root_node_name: "Access to Healthy Food"
root_question: "What are the main obstacles to increasing community access to healthy food?"
locality: "Springfield"
country: "USA"
major_theme_obstacles:
  - "Lack of grocery stores"
  - "Limited public transportation"
  - "High food prices"
```

---

## Running the Project

1. **Activate your virtual environment** (see below).

2. **Ensure your `.env` file is in the project root** with your OpenAI credentials:
   ```
   OPENAI_API_KEY=sk-...
   OPENAI_ORG=org-...
   ```

3. **Create a new project directory in `projects/`** and add a `config.yaml` file as shown above.

4. **Run the GOSR workflow:**

   ```sh
   # Generate obstacles
   python scripts/main/g2o.py path-to-project

   # Generate solutions
   python scripts/main/o2s.py path-to-project

   # Generate resources
   python scripts/main/s2r.py path-to-project
   ```

5. **Clean `resources-raw.json` into `resources.json`:**
   ```sh
   python scripts/utils/raw2resources.py path-to-project
   ```

6. **(Optional) Use conversion/export scripts:**

   - **Generate DOCX outline:**
     ```sh
     python scripts/convert/json2doc.py path-to-project --stage s
     python scripts/convert/json2doc.py path-to-project --stage r
     ```

   - **Generate FreeMind mind map:**
     ```sh
     python scripts/convert/json2mm.py path-to-project --stage s
     python scripts/convert/json2mm.py path-to-project --stage r
     ```

   - **Generate Google Maps CSVs and mailing list:**
     ```sh
     python scripts/convert/r2google-maps.py path-to-project
     ```

   - **Fix solution/resource mappings:**
     ```sh
     python scripts/convert/json2map.py path-to-project --stage r
     python scripts/convert/json2map.py path-to-project --stage s
     ```

   - **Recheck and clean resource URLs:**
     ```sh
     python scripts/utils/recheck_resource_urls.py path-to-project
     ```

---

## Setting up a Python Virtual Environment

1. **Create a virtual environment (recommended: `.venv`):**

   On Linux/macOS/WSL:
   ```sh
   python3 -m venv .venv
   ```

   On Windows:
   ```sh
   python -m venv .venv
   ```

2. **Activate the virtual environment:**

   On Linux/macOS/WSL:
   ```sh
   source .venv/bin/activate
   ```

   On Windows:
   ```sh
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **(Optional) Add new packages:**
   ```sh
   pip install <package-name>
   pip freeze > requirements.txt
   ```

5. **Deactivate the environment when done:**
   ```sh
   deactivate
   ```

**Note:**  
- Always activate your virtual environment before running scripts.
- Never commit your `.env` file or `.venv` directory to git.

---

## Reference

For more details on the GOSR process, see  
https://docs.google.com/presentation/d/1wLkb61LRHV_3o0JqQnr0yeqTPRzzKiLhw0elX2_o6M8/edit?slide=id.g1ff3a93b48e_0_5

**Tip:**  
You can create multiple project directories for different goals or communities and run the workflow independently for each.