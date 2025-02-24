from src.managers import DatasetManager, MongoDBManager, PromptManager

from .src.utils.prompts import SYSTEM_TEMPLATE, USER_TEMPLATE

db_manager = MongoDBManager(db_name="physiq_db")
dataset_mgr = DatasetManager(db_manager)
prompt_mgr = PromptManager(SYSTEM_TEMPLATE, USER_TEMPLATE)

# 1) Retrieve the puzzle+proposal data
sample = dataset_mgr.get_sample(
    puzzle_id="00012:001", proposal_tier="CORRECT", num_frames=3, few_shot_count=2
)

# 2) Build the final prompt
prompt = prompt_mgr.build_prompt(
    puzzle_data=sample["puzzle"],
    proposal_data=sample["proposal"],
    images=sample["images"],
    few_shot_examples=sample["few_shot"],
)

print("=== SYSTEM PROMPT ===")
print(prompt["system"])
print("\n=== USER PROMPT ===")
print(prompt["user"])
