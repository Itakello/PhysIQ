import base64
import os
import random
from typing import Any

from loguru import logger
from tqdm import tqdm

from prompt_tester import select_representative_frames
from src.evaluation.interactive_eval import (
    evaluate_interactive_response,
    generate_feedback_message,
)
from src.managers import ArgparseManager, DatasetManager, MongoDBManager, PromptManager
from src.utils.db_schemas import (
    EvaluationResultSchema,
    ProposalSchema,
    RankingProposalItem,
    RankingSampleData,
    SampleData,
)
from src.utils.vlm_client import VLMClient


def get_sample(
    eval_type: str,
    dataset_manager: DatasetManager,
    proposal,
    few_shot_count: int,
    few_shot_frames: int = 1,
) -> SampleData | RankingSampleData | None:
    """Retrieve the appropriate sample based on evaluation type."""
    if eval_type == "sanity_check":
        return dataset_manager.get_sanity_check_sample(proposal.id, proposal.tier, few_shot_count=few_shot_count)  # type: ignore
    elif eval_type == "ranking":
        # For ranking, we use 1 frame as per prompt_tester logic
        return dataset_manager.get_ranking_sample(proposal.id, 1, few_shot_count=few_shot_count)  # type: ignore
    elif eval_type == "binary":
        return dataset_manager.get_binary_sample(proposal.id, 1, proposal.tier, few_shot_count=few_shot_count, few_shot_frames=few_shot_frames)  # type: ignore
    elif eval_type == "confidence":
        # For confidence evaluation, we use binary sample retrieval with no few-shot examples
        return dataset_manager.get_binary_sample(proposal.id, 1, proposal.tier, few_shot_count=0, few_shot_frames=0)  # type: ignore
    elif eval_type == "interactive":
        # For interactive evaluation, we use binary sample retrieval with specified few-shot examples
        return dataset_manager.get_interactive_sample(proposal.id)  # type: ignore
    else:
        logger.error(f"Evaluation type {eval_type} not supported for sample retrieval.")
        return None


def determine_correctness(
    eval_type: str,
    proposal: ProposalSchema | RankingProposalItem,
    model_answer: str,
    sample: SampleData | RankingSampleData,
) -> tuple[bool, Any]:
    """Determine whether the model answer is correct and return the expected answer.

    For sanity_check, expected answer is 'yes' for CORRECT tier and 'no' otherwise.
    For ranking, expected answer is a list of indexes from sample.metadata.correct_ranking. The model_answer is parsed to a list of integers.
    For interactive, expected answer is 'GOAL_REACHED' and the model_answer is the final status from the interactive evaluation.
    """
    if eval_type == "sanity_check" or eval_type == "binary":
        expected_answer = "yes" if proposal.tier.upper() == "CORRECT" else "no"
        correct = expected_answer in model_answer.lower().strip()
        return correct, expected_answer
    elif eval_type == "ranking":
        if not hasattr(sample, "metadata"):
            logger.error(
                "Sample for ranking evaluation must have a 'metadata' attribute with correct_ranking"
            )
            return False, []
        expected_ranking: list[int] = [rank + 1 for rank in sample.metadata.correct_ranking]  # type: ignore
        try:
            import re

            numbers = re.findall(r"\d+", model_answer)
            parsed_answer = list(map(int, numbers))[-4:]
        except Exception as e:
            logger.error(f"Error parsing model answer for ranking evaluation: {e}")
            parsed_answer = []
        correct = parsed_answer == expected_ranking
        return correct, expected_ranking
    elif eval_type == "interactive":
        # For interactive evaluation, the model_answer is the final status
        # and we consider it correct if the status is GOAL_REACHED
        expected_answer = "GOAL_REACHED"
        correct = model_answer == expected_answer
        return correct, expected_answer
    else:
        logger.error(
            f"Unsupported evaluation type {eval_type} for determining correctness"
        )
        return False, None


def main() -> None:
    """Main function for the evaluation pipeline."""
    # Initialize argument parser
    parser = ArgparseManager(description="PhysIQ VLM Evaluation Pipeline")
    parser.add_common_db_args()
    parser.add_common_simulation_args()
    parser.add_evaluation_args()
    parser.add_seed_args()

    # Parse arguments
    args = parser.parse_args()

    # Validate and process arguments
    if args.iterations > 20:
        logger.warning("Limiting iterations to 20")
        args.iterations = 20

    # Initialize managers
    mongo_manager = MongoDBManager(db_name=args.db_name)
    dataset_manager = DatasetManager(db_manager=mongo_manager)

    eval_type = args.evaluation_type

    if eval_type not in [
        "sanity_check",
        "ranking",
        "binary",
        "confidence",
        "interactive",
    ]:
        logger.error(
            "Currently only the 'sanity_check', 'ranking', 'binary', 'confidence', and 'interactive' evaluations are implemented."
        )
        return

    # random.seed(args.seed)

    # Create prompt manager for the given evaluation type
    prompt_manager = PromptManager(prompt_type=eval_type)

    # Get all proposals within the specified template and iteration range
    all_proposals = mongo_manager.get_all_proposals(
        start_template=args.start_template,
        stop_template=args.stop_template,
    )

    # Group proposals by template id and tier
    grouped_proposals: dict[int, dict[str, list]] = {}
    for proposal in all_proposals:
        template_id = int(proposal.id.split(":")[0])
        tier = proposal.tier
        if template_id not in grouped_proposals:
            grouped_proposals[template_id] = {}
        grouped_proposals[template_id].setdefault(tier, []).append(proposal)

    # Initialize VLM client
    vlm_client = VLMClient()
    if not vlm_client.is_configured():
        logger.error(
            "OpenRouter API key not configured. Please set OPENROUTER_API_KEY environment variable."
        )
        return

    # If 'all' is specified in the --models argument, use all available models
    if "all" in args.models:
        args.models = vlm_client.ALL_MODELS

    # Iterate over each template and proposal type group with a main progress bar
    for template_id in tqdm(
        sorted(grouped_proposals.keys()), desc="Templates", unit="template"
    ):
        if eval_type == "sanity_check":
            correct_proposals = grouped_proposals[template_id].get("CORRECT", [])
            incorrect_proposals = []
            for tier, proposals in grouped_proposals[template_id].items():
                if tier != "CORRECT":
                    incorrect_proposals.extend(proposals)
            selected_correct = (
                random.sample(correct_proposals, args.iterations)
                if correct_proposals
                else []
            )
            selected_incorrect = (
                random.sample(incorrect_proposals, args.iterations)
                if incorrect_proposals
                else []
            )
            selected_proposals = selected_correct + selected_incorrect
        elif eval_type in ["binary", "confidence"]:
            selected_proposals = []
            for tier, proposals in grouped_proposals[template_id].items():
                if proposals:
                    sample_size = (
                        args.iterations
                        if len(proposals) >= args.iterations
                        else len(proposals)
                    )
                    selected_proposals.extend(random.sample(proposals, sample_size))
        elif eval_type in ["ranking", "interactive"]:
            proposals = grouped_proposals[template_id].get("CORRECT", [])
            selected_proposals = random.sample(proposals, args.iterations)
        else:
            selected_proposals = []

        # Progress bar for proposals loop (disappears after completion)
        for proposal in tqdm(
            selected_proposals, desc="Proposals", unit="proposal", leave=False
        ):
            # Get the sample using the helper function based on evaluation type
            sample = get_sample(
                eval_type,
                dataset_manager,
                proposal,
                args.few_shot_count,
                args.few_shot_frames,
            )
            if not sample:
                logger.error(f"No sample found for ID {proposal.id}")
                continue

            messages = prompt_manager.build_openai_messages(
                sample,
                insert_few_shot=(eval_type != "confidence" and args.few_shot_count > 0),
            )

            # Evaluate for all models provided with a progress bar (disappears after completion)
            for model in tqdm(args.models, desc="Models", unit="model", leave=False):
                logger.debug(
                    f"Sending prompt to model {model} for sample {proposal.id}..."
                )

                if eval_type == "interactive":
                    # For interactive evaluation, we need to handle multiple attempts
                    max_attempts = (
                        5  # Maximum number of attempts for interactive evaluation
                    )
                    attempt_statuses = []
                    final_status = (
                        "GOAL_NOT_REACHED"  # Default status if all attempts fail
                    )

                    for attempt_number in range(1, max_attempts + 1):
                        # Get model response for this attempt
                        response = vlm_client.send_message(messages, model)

                        # Evaluate the interactive response
                        eval_result = evaluate_interactive_response(
                            response=response,
                            puzzle=sample.puzzle.model_dump(),
                            visualize=False,
                            num_screenshots=10,
                        )

                        # Record the status for this attempt
                        attempt_statuses.append(eval_result.status)

                        # If goal reached, we're done
                        if eval_result.status == "GOAL_REACHED":
                            final_status = "GOAL_REACHED"
                            break

                        # Generate feedback for the next attempt
                        feedback = generate_feedback_message(
                            eval_result.status, attempt_number
                        )

                        # Add the feedback to the messages for the next attempt
                        # Create proper assistant message with the actual LLM response
                        messages.append({"role": "assistant", "content": response})

                        user_content = []
                        if eval_result.screenshots:
                            selected_screenshots = select_representative_frames(
                                eval_result.screenshots, max_frames=5
                            )
                            parts = feedback.split("[IMAGES]")

                            user_content.append({"type": "text", "text": parts[0]})

                            for screenshot in selected_screenshots:
                                with open(screenshot, "rb") as f:
                                    img_data = f.read()
                                    encoded_img = base64.b64encode(img_data).decode(
                                        "utf-8"
                                    )
                                    user_content.append(
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:image/png;base64,{encoded_img}",
                                                "detail": "high",
                                            },
                                        }
                                    )
                            user_content.append({"type": "text", "text": parts[1]})
                        else:
                            user_content.append({"type": "text", "text": feedback})

                        messages.append({"role": "user", "content": user_content})

                    # Use the final status as the model answer
                    model_answer = final_status

                else:
                    # For other evaluation types, just get a single response
                    response = vlm_client.send_message(messages, model)

                    if isinstance(response, list):
                        model_answer = " ".join(str(item) for item in response)
                    else:
                        model_answer = response
                    model_answer = model_answer.lower().strip()
                    attempt_statuses = None

                if eval_type == "confidence":
                    # For confidence evaluation, we do not verify; always record False and ground_truth as None
                    correct = False
                    expected_answer = None
                    logger.debug(f"{proposal.id}: Confidence {model_answer}")
                else:
                    correct, expected_answer = determine_correctness(
                        eval_type, proposal, model_answer, sample
                    )
                    logger.debug(f"{proposal.id}: {correct}")

                result = EvaluationResultSchema(
                    evaluation_type=eval_type,
                    model_name=model,
                    sample=sample,
                    few_shot_count=(
                        0 if eval_type == "confidence" else args.few_shot_count
                    ),
                    few_shot_frames=(
                        0 if eval_type == "confidence" else args.few_shot_frames
                    ),
                    correct=correct,
                    ground_truth=expected_answer,
                    response=model_answer,
                    attempt_statuses=attempt_statuses,
                )
                if args.save_to_db:
                    mongo_manager.insert_evaluation_result(result)

    logger.info(f"{eval_type} evaluation completed and results stored in MongoDB.")


if __name__ == "__main__":
    main()
