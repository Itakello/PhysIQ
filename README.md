# 🧠 PhysIQ: A Vision Language Model Benchmark for Physical Reasoning

This repository contains a comprehensive evaluation framework for testing Vision Language Models (VLMs) on physical reasoning tasks. Built on top of the [PHYRE](https://github.com/facebookresearch/phyre) benchmark, it provides a structured way to assess how well VLMs can understand and reason about physical interactions in a 2D environment.

## 🌟 Features

- Multiple evaluation types: sanity check, ranking, binary classification, confidence assessment, and interactive problem-solving
- Integration with OpenRouter API for easy access to various VLMs
- Interactive visualization tool for prompt testing
- Comprehensive evaluation pipeline with detailed metrics
- Support for both 1-ball and 2-ball physics puzzles

## 📚 Thesis and Results

This project has been extensively documented in the thesis available in `main.pdf`. The thesis includes:
- Detailed methodology and implementation
- Comprehensive analysis of results across different evaluation types
- Comparison of various VLM models
- Insights into model performance and limitations
- Future work and potential improvements

For a complete understanding of the project's findings and analyses, please refer to the thesis document.

## 🚀 Getting Started

### Prerequisites

- Python 3.10+ (except for `0_extract_jsons.py` which requires Python 3.6)
- MongoDB installed locally
- OpenRouter API key (for VLM integration)

### Initial Setup

1. Clone the repository:
    ```sh
    git clone https://github.com/Itakello/physiq.git
    cd physiq
    ```

2. Create and activate a conda environment:
    ```sh
    conda create -n physiq python=3.10
    conda activate physiq
    ```

3. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4. Download required data:
   - Download the images folder and MongoDB backup from [OneDrive](https://1drv.ms/f/s!AtXdrMCFZ47igrlGhkIGnqE5J83TTw?e=nxCd1n)
   - Extract the MongoDB backup to your local MongoDB instance
   - Place the images in the appropriate directory

5. Set up your OpenRouter API key:
    ```sh
    export OPENROUTER_API_KEY=your_api_key_here
    ```

## 📁 Scripts Overview

All scripts should be run as modules from the root directory using the format:
```sh
python -m scripts.<script_name> [arguments]
```

To see available parameters for any script, use the `-h` flag:
```sh
python -m scripts.<script_name> -h
```

### Available Scripts

1. `0_extract_jsons.py` 🔄
   - Extracts puzzle parameters from PHYRE into JSON format
   - Requires Python 3.6
   - Usage: `python -m scripts.0_extract_jsons --output-dir puzzle_jsons`

2. `1_move_to_db.py` 📦
   - Moves extracted JSON puzzles to MongoDB
   - Creates initial database structure
   - Usage: `python -m scripts.1_move_to_db --db-name physiq`

3. `2_simulation_testing.py` 🎮
   - Tests physics simulation for puzzles
   - Validates puzzle behavior and constraints
   - Usage: `python -m scripts.2_simulation_testing --db-name physiq`

4. `3_correct_proposals_identification.py` ✅
   - Identifies and marks correct puzzle solutions
   - Validates solution effectiveness
   - Usage: `python -m scripts.3_correct_proposals_identification --db-name physiq`

5. `4_incorrect_proposals_identification.py` ❌
   - Generates and validates incorrect solutions
   - Creates negative examples for training
   - Usage: `python -m scripts.4_incorrect_proposals_identification --db-name physiq`

6. `5_evaluation.py` 📊
   - Main evaluation pipeline for testing VLMs
   - Supports multiple evaluation types and models
   - Usage: `python -m scripts.5_evaluation --evaluation-type [type] --models [model_names]`

7. `6_plot_stats.py` 📈
   - Generates evaluation statistics and visualizations
   - Creates performance reports and graphs
   - Usage: `python -m scripts.6_plot_stats --db-name physiq`

8. `add_test_puzzles.py` 🧪
   - Adds test puzzles to the database
   - Useful for development and testing
   - Usage: `python -m scripts.add_test_puzzles --db-name physiq`

## 🎮 Interactive Testing

Use the `prompt_tester.py` script with Streamlit to interactively test and visualize different evaluation types:
```sh
streamlit run prompt_tester.py
```

This will launch a Streamlit interface where you can:
- Select different evaluation types
- Choose specific puzzles to test
- Configure few-shot examples
- Test different VLM models
- Visualize prompts and responses

## 🔍 Evaluation Types

1. **Sanity Check** ✅
   - Basic verification of model's understanding
   - Tests if model can identify correct solutions

2. **Ranking** 📈
   - Evaluates model's ability to rank solutions by quality
   - Tests relative understanding of physical interactions

3. **Binary Classification** ⚖️
   - Simple correct/incorrect classification
   - Tests basic physical reasoning capabilities

4. **Confidence Assessment** 🎯
   - Measures model's confidence in its predictions
   - Helps identify overconfident or uncertain responses

5. **Interactive Problem-Solving** 🎮
   - Multi-turn problem-solving with feedback
   - Tests model's ability to learn from failures

## 📊 Running the Benchmark

For detailed information on how to run the benchmark and reproduce our results, refer to the `5_evaluation.py` script. It contains comprehensive documentation and examples of different evaluation configurations.

## 🔧 Development

The project follows a modular architecture:
- `src/`: Core source code
  - `managers/`: Database and dataset management
  - `evaluation/`: Evaluation logic and metrics
  - `utils/`: Helper functions and schemas
- `scripts/`: Utility scripts for data processing and evaluation
- `prompt_tester.py`: Interactive testing interface

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [PHYRE](https://github.com/facebookresearch/phyre) - The base physics reasoning benchmark
- [OpenRouter](https://openrouter.ai/) - For providing access to various VLMs
- [Box2D](https://box2d.org/) - For the physics simulation engine
