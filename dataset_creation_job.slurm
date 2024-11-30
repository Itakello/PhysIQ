#!/bin/bash
#SBATCH --job-name=lower_time_scale
#SBATCH --partition=gpu
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2l
#SBATCH --gpus=1
#SBATCH --time=48:00:00
#SBATCH --mem=4G
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err

# Load necessary modules
module load 2023
module load Miniconda3/23.5.2-0

# Activate your virtual environment if you're using one
# source /path/to/your/venv/bin/activate
conda create -n myenv python=3.10
conda activate myenv
pip install -r requirements.txt

python main.py -c lower_time_scale
