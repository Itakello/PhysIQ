# My Project

## Setup

1. Create a conda environment with Python 3.10:
    ```sh
    conda create -n myproject python=3.10
    ```

2. Activate the conda environment:
    ```sh
    conda activate myproject
    ```

3. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

Run the main application:
```sh
python main.py
```

This will iterate over all the levels. A play-stop button is present with the idea of adding other controls (e.g., solution) in the future.

## Upcoming Features

- Possibility to add other bodies (for next step)
- Possibility to insert bodies without interpolation automatically/manually (for next step)
- Possibility to verify solutions via goals
- Brute-force add 1 solution to every level (by changing circle size/position)
- Find way to find multiple correct and incorrect solutions by changing parameters programmatically
- Creation of a static dataset (image + prompt + correct/incorrect) for fast execution
- Possibility for an LVLM (Large Vision Language Model) to test it
- Possibility to test multiple LVLMs by their Hugging Face model name

## Future Complex Feature (Time Permitting)

- Level-creator environment to generate new starting configurations:
  - Create 1 starting configuration
  - Programmatically generate 25 variations for easy scaling

## Known Issues

- Some solutions converted from Phyre may not be solutions in our environment with PyMunk or may be trivial

## References

- Phyre: [https://phyre.ai/](https://phyre.ai/)
- PyMunk: [https://www.pymunk.org/en/latest/overview.html](https://www.pymunk.org/en/latest/overview.html)
