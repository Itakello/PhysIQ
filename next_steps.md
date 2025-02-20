## Goal

Create a benchmark for Large Language Models (LLMs) to assess their physical reasoning abilities in a simplified physical environment.

There are two main tasks:

1. **Task 1 – Non-Interactive (Static)**: Given a configuration (image + hyperparameters description), predict whether the goal (two specific objects coming into contact) will be reached.

2) **Task 2 – Interactive**: Enable the LLM to determine the position and radius of a ball to be inserted into the simulation to achieve the goal.

## What Has Already Been Done

1. **Dataset Conversion**:
   1. Reverse-engineered the Phyre dataset to simulate tasks similar to the original.
   2. Constructed 50 templates (25 with 1 ball and 25 with 2 balls) with each template having 100 iterations.
      Configurations include:
      1. The bodies (position, size, color, type, etc.)
      2. The 2 objects that should touch in the end.
2. **Simulation**:
   1. Implemented physical simulation using pymunk.
   2. Visualized configurations using pygame to ensure consistency and human-presentable format.
3. **Proposal Generation**:
   1. Manually generated solutions (via brute-force) to reach the goals.
   2. Reimplemented the solution generation to:
   3. Adapt to slight differences in the environment.
   4. Ensure extensibility of the framework.
4. **Solution Verification**:
   1. Iteratively tested the generated proposals.
   2. Verified that the goal was reached within a set threshold or when no more objects were moving.
5. **Dataset Creation**:
   1. Composed dataset samples that include:
      1. An image (the starting configuration)
      2. The task description (with physical parameters)
      3. The ground truth (for Task 1 only; Task 2 will be programmatically evaluated)
   2. Targeted having 5 good/bad solutions per iteration.

## ✅ PhysIQ To-Do List with Subtasks

#### **1️⃣ Refactor the Codebase**

- [ ] 🔧 **Split code into main operation scripts**
  - [x] Create `0_extract_jsons.py` - Extract the puzzles metadata from phyre (uses python 3.8 beacause of phyre old repository)
  - [x] Create `1_move_to_db.py` - Create the mongoDB database + move the puzzles to the DB
  - [x] Create `2_simulation_testing.py` - Simulate the puzzles using pybox2d
  - [ ] Create `3_proposals_identification.py` - Brute-force the proposals findings by verification (x good proposals and x bad proposals) and store them in MongoDB in a new table + the images
  - [ ] Create `4_offline_evaluation.py` - Evaluate 1 or more LLMs with 3 different prompts
  - [ ] Create `5_online_evaluation.py` - Evaluate 1 or more LLMs with 3 different prompts
  - [ ] Create `6_create_human_interface.py` - Create a webapp and a submission module for humans evaluation
  - [ ] Create `7_plot_results.py` - Plot the results of the experiments
  - [ ] Create `8_dataset_expansion.py` - Build in a programmatic way new templates and iterations. Take inspiration from phyre scripts.
- [ ] 🏗️ **Refactor into modular functions**
  - [ ] Move reusable functions to utility modules
  - [ ] Ensure each script only calls relevant modules
- [ ] ✅ **Standardize script structure**
  - [ ] Implement `main(args)` function
  - [ ] Use `argparse` for argument parsing
  - [ ] Ensure all scripts follow the same format

#### **2️⃣ Dataset Storage**

- [ ] 📂 **Decide how to store configuration parameters & images**
  - [x] Reorganize the dataset structure
  - [x] Choose between JSON, CSV, or other formats for parameters
  - [ ] Define a naming convention for image storage
  - [ ] Integrate with Hugging Face Datasets
  - [ ] Integrate with the `datasets` library

#### **3️⃣ Engine Conversion (PyBox2D Migration)**

- [x] 🔬 **Analyze PhyRE repo**
  - [x] Identify physical hyperparameters used and their values
  - [x] Understand how PhyRE stores physical parameters
  - [x] Study how solutions are generated
  - [x] Analyze how PhyRE validates solutions efficiently
- [x] 🛠️ **Understand PyBox2D mechanics**
  - [x] Simulate existing templates in PyBox2D
  - [x] Implement brute-force solution finding
  - [x] Implement solution verification and optimize for speed

#### **4️⃣ Offline Evaluation**

- [ ] 📝 **Setup 3 different prompts for evaluation** (with and without hyperparameters + another idea)
- [ ] ⚙ **Integrate with Weave**
  - [ ] Research how to use Weave
  - [ ] Test prompts on a single model
  - [ ] Run evaluation on a small set of examples for each template

#### **5️⃣ Online Evaluation**

- [ ] 🔄 **Test the Clembench framework**
  - [ ] Run a sample test to understand how it works
  - [ ] Connect the benchmark to the Clembench APIs
  - [ ] Adapt it to PhysIQ tasks
- [ ] 🎯 **Prepare different prompts for online evaluation**
- [ ] 🧠 **Evaluate a single LLM using Weave**
  - [ ] Ensure prompts work correctly for different templates

#### **6️⃣ Run Full Evaluation**

- [ ] 📊 **Evaluate all models** (GPT-4o by OpenAI, Gemini 1.5 Pro by Google,Claude 3.5 Sonnet by Anthropic, Falcon 2 Series by UAE, DeepSeek-VL)
  - [ ] Decide number of iterations per template based on cost and time constraints
  - [ ] Run both offline and online evaluations
  - [ ] Log and store results systematically

#### **7️⃣ Set up evaluation with human participants**

- [ ] 🌐 **Decide on the platform (website, form, or both)**
- [ ] 🏗 **Develop the interface**
  - [ ] Set up a simple frontend for data collection (via streamlit)
  - [ ] Integrate submission system
#### **8️⃣ Results Analysis & Visualization**

- [ ] 📈 **Plot results**
  - [ ] Generate visualizations for performance metrics
  - [ ] Compare different LLMs and reasoning approaches
- [ ] 🔍 **Perform statistical analysis**
  - [ ] Identify key trends and insights
  - [ ] Summarize findings for final documentation


#### **9️⃣ Repository Finalization**

- [ ] 🧹 **Polish and finalize the repository**
- [ ] **✍🏻** **Add a final README detailing the project, setup instructions, and usage**

#### **📝 Final Step: Report & Thesis Writing**

- [ ] 📑 **Write the final report** (structured, concise, and formal)
- [ ] 📖 **Expand the report into the thesis**
  - [ ] Include background, methodology, results, and conclusions
