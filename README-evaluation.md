# PhysIQ Evaluation System

This document describes the evaluation system for the PhysIQ project, which assesses how well different vision-language models (VLMs) perform on physics-based reasoning tasks.

## Overview

The evaluation system tests VLMs on multiple types of physics reasoning challenges:

1. **Binary Classification** - Tests if a model can correctly classify a physics simulation outcome as successful or not
2. **Ranking** - Tests if a model can rank multiple proposals by their likelihood of success
3. **Sanity Check** - Tests if a model can correctly identify obvious physics violations
4. **Interactive** - Tests a model's ability to reason about physical interactions in multi-turn dialogues

## Requirements

- Python 3.10+
- MongoDB (for storing datasets)
- Weights & Biases account (for tracking experiments)
- API keys for supported VLMs

## Installation

```bash
# Install required packages
pip install wandb tqdm loguru pymongo
```

## Usage

The evaluation system can be run via the `scripts/5_interactive_evaluation.py` script. You can configure it using various command-line arguments:

```bash
python -m scripts.5_interactive_evaluation \
  --models openai/gpt-4o anthropic/claude-3-5-sonnet \
  --start_template 0 \
  --stop_template 5 \
  --iterations 2 \
  --evaluation_types binary ranking \
  --few_shot_count 1 \
  --few_shot_frames 1 \
  --output_dir evaluation_results \
  --use_wandb \
  --wandb_project physiq-model-evaluations
```

### Key Arguments

- `--models`: One or more VLM models to evaluate
- `--start_template`/`--stop_template`: Range of template IDs to evaluate
- `--iterations`: Number of iterations per template
- `--evaluation_types`: Types of evaluation to run (binary, ranking, sanity_check, interactive, all)
- `--few_shot_count`: Number of few-shot examples to include (0-4)
- `--few_shot_frames`: Number of frames per few-shot example (1-5)
- `--output_dir`: Directory to save evaluation results
- `--use_wandb`: Enable Weights & Biases tracking
- `--wandb_project`: W&B project name
- `--wandb_entity`: W&B entity (username or team)

## Evaluation Metrics

The system tracks several metrics for each evaluation:

- **Success Rate**: Percentage of successfully completed evaluations
- **Response Length**: Length of the model's responses
- **Accuracy** (computed after evaluation): How often the model correctly identified the physics outcome

## Weights & Biases Integration

The system integrates with Weights & Biases to track experiments:

1. **Run Configuration**: Each model gets its own W&B run with configuration details
2. **Metrics**: Progress metrics are logged during evaluation
3. **Results Comparison**: Compare performance across different models and evaluation types

To view results:
1. Log in to your W&B account
2. Navigate to the project (default: physiq-model-evaluations)
3. Use the W&B dashboard to compare runs and analyze results

## Launch Configurations

For convenience, VS Code launch configurations are provided in `.vscode/launch.json`:

- **5 - Interactive Evaluation**: Runs evaluation with W&B tracking
- **5 - Non-interactive Evaluation**: Runs alternative evaluation script

## Argument Management

The evaluation script uses the `ArgparseManager` class to handle command-line arguments:

- `add_evaluation_args()` - Adds evaluation-specific arguments
- `add_wandb_args()` - Adds Weights & Biases tracking arguments
- `add_common_db_args()` - Adds MongoDB database arguments

This modular approach makes it easy to reuse argument configurations across different scripts.

## Troubleshooting

- **Model API Errors**: Ensure you have the correct API keys configured for each model
- **W&B Login Issues**: Run `wandb login` manually to authenticate
- **MongoDB Connection**: Ensure MongoDB is running and accessible

## Adding New Models

To add support for a new model:

1. Update the VLMClient class in `src/utils/vlm_client.py`
2. Add the model to the prompt formats in PromptManager
3. Test with a small evaluation run before scaling up

## License

This project is part of the PhysIQ research effort. See the main project license for details. 