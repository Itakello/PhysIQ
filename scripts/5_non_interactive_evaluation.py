import json

from loguru import logger

from src.managers import ArgparseManager, DatasetManager, MongoDBManager, PromptManager
from src.utils.const import (
    PROMPT_COT,
    PROMPT_DETAILED,
    PROMPT_DIRECT,
    PROMPT_SANITY_CHECK,
)
from src.utils.prompts import SYSTEM_TEMPLATES


def main() -> None:
    parser = ArgparseManager(description="Test the PromptManager")
    parser.add_common_db_args()
    parser.add_model_args()
    args = parser.parse_args()

    logger.info("Starting prompt generation test")

    # Initialize managers
    mongo_manager = MongoDBManager(db_name="physiq_db")
    dataset_manager = DatasetManager(db_manager=mongo_manager)

    # Create prompt managers for different prompt types
    prompt_managers = {
        PROMPT_DIRECT: PromptManager(
            prompt_type=PROMPT_DIRECT, system_template=SYSTEM_TEMPLATES[PROMPT_DIRECT]
        ),
        PROMPT_DETAILED: PromptManager(
            prompt_type=PROMPT_DETAILED,
            system_template=SYSTEM_TEMPLATES[PROMPT_DETAILED],
        ),
        PROMPT_COT: PromptManager(
            prompt_type=PROMPT_COT, system_template=SYSTEM_TEMPLATES[PROMPT_COT]
        ),
        PROMPT_SANITY_CHECK: PromptManager(
            prompt_type=PROMPT_SANITY_CHECK,
            system_template=SYSTEM_TEMPLATES[PROMPT_SANITY_CHECK],
        ),
    }

    # Get a sample with few-shot examples
    sample_data = dataset_manager.get_sample(
        "00124:002", 1, "CORRECT", few_shot_count=2
    )

    # Generate messages for each prompt type
    for prompt_name, prompt_manager in prompt_managers.items():
        logger.info(f"Generating {prompt_name} prompt")

        # Generate messages with few-shot examples
        messages = prompt_manager.build_openai_messages(
            sample_data, insert_few_shot=True
        )

        # Print the messages content
        print(f"\n{prompt_name} Prompt (With Few-Shot Examples):")
        print(json.dumps(messages, indent=2))

        logger.info(f"Generated {prompt_name} prompt with {len(messages)} messages")

        # Here you would send these messages to your model
        # model_response = send_to_model(messages)
        # ...evaluation logic would go here...


if __name__ == "__main__":
    main()
