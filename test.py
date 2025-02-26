import json
from pathlib import Path

from loguru import logger

from src.managers import DatasetManager, MongoDBManager, PromptManager
from src.utils.const import PROMPT_COT, PROMPT_DETAILED, PROMPT_DIRECT


def main() -> None:
    """Test the PromptManager with different prompt types."""
    logger.info("Starting prompt generation test")

    # Initialize managers
    mongo_manager = MongoDBManager(db_name="physiq_db")
    dataset_manager = DatasetManager(db_manager=mongo_manager)

    prompt_managers = {
        PROMPT_DIRECT: PromptManager(prompt_type=PROMPT_DIRECT),
        PROMPT_DETAILED: PromptManager(prompt_type=PROMPT_DETAILED),
        PROMPT_COT: PromptManager(prompt_type=PROMPT_COT),
    }

    # Get a sample with few-shot examples
    sample_data = dataset_manager.get_sample("124:002", 1, "CORRECT", few_shot_count=2)

    # Test all prompt types with and without few-shot examples
    for prompt_name, prompt_manager in prompt_managers.items():
        logger.info(f"\n--- Testing {prompt_name} Prompt ---")

        # Test without few-shot examples
        messages = prompt_manager.build_openai_messages(
            sample_data, insert_few_shot=False
        )
        print(f"\n{prompt_name} Prompt (No Few-Shot):")
        print(json.dumps(messages, indent=2))

        # Test with few-shot examples
        messages_with_fewshot = prompt_manager.build_openai_messages(
            sample_data, insert_few_shot=True
        )
        print(f"\n{prompt_name} Prompt (With Few-Shot Examples):")
        print(json.dumps(messages_with_fewshot, indent=2))


if __name__ == "__main__":
    main()
