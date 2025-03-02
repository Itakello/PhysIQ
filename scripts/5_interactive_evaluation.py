import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

import weave
from loguru import logger
from tqdm import tqdm

from src.managers import ArgparseManager, DatasetManager, MongoDBManager, PromptManager
from src.utils.vlm_client import VLMClient
from src.utils.weave_verifier import WeaveVerifier


def evaluate_model_on_samples(
    model_name: str,
    dataset_manager: DatasetManager,
    prompt_manager: PromptManager,
    vlm_client: VLMClient,
    verifier: WeaveVerifier,
    template_range: range,
    iterations: int,
    prompt_type: str,
    output_dir: Path,
    few_shot_count: int = 0,
    few_shot_frames: int = 1,
) -> Dict[str, Any]:
    """
    Evaluate a model on a range of templates and iterations.

    Args:
        model_name: Name of the model to evaluate
        dataset_manager: Dataset manager instance
        prompt_manager: Prompt manager instance
        vlm_client: VLM client instance
        verifier: WeaveVerifier instance for evaluation
        template_range: Range of template IDs to evaluate
        iterations: Number of iterations per template
        prompt_type: Type of prompt to use
        output_dir: Directory to save results
        few_shot_count: Number of few-shot examples to include
        few_shot_frames: Number of frames per few-shot example

    Returns:
        Dictionary containing evaluation results
    """
    results = {
        "model": model_name,
        "prompt_type": prompt_type,
        "few_shot_count": few_shot_count,
        "few_shot_frames": few_shot_frames,
        "samples": [],
    }

    successful_samples = 0
    total_samples = 0

    # Get the Weave model from the VLM client
    weave_model = vlm_client.get_or_create_weave_model(model_name)

    for template_id in tqdm(template_range, desc=f"Templates ({prompt_type})"):
        for iteration_id in range(iterations):
            sample_id = f"{template_id:05d}:{iteration_id:03d}"
            total_samples += 1

            # Skip if we don't have this sample
            try:
                if prompt_type == "ranking":
                    sample = dataset_manager.get_ranking_sample(
                        sample_id,
                        1,  # Always use 1 frame for ranking
                        few_shot_count=few_shot_count,
                    )
                elif prompt_type == "sanity_check":
                    # Cast to handle type compatibility
                    base_sample = dataset_manager.get_sanity_check_sample(
                        sample_id, "CORRECT", few_shot_count=few_shot_count
                    )
                    sample = base_sample  # Type assignment handled in evaluation
                elif prompt_type == "interactive":
                    # Cast to handle type compatibility
                    base_sample = dataset_manager.get_interactive_sample(sample_id)
                    sample = base_sample  # Type assignment handled in evaluation
                else:  # binary
                    # Cast to handle type compatibility
                    base_sample = dataset_manager.get_binary_sample(
                        sample_id,
                        1,
                        "CORRECT",
                        few_shot_count=few_shot_count,
                        few_shot_frames=few_shot_frames,
                    )
                    sample = base_sample  # Type assignment handled in evaluation

                # Generate messages
                messages = prompt_manager.build_openai_messages(
                    sample, insert_few_shot=(few_shot_count > 0)
                )

                # Add metadata to log with Weave
                metadata = {
                    "sample_id": sample_id,
                    "prompt_type": prompt_type,
                    "template_id": template_id,
                    "iteration_id": iteration_id,
                    "few_shot_count": few_shot_count,
                }

                # Send to model
                try:
                    # VLM client now handles Weave tracing internally
                    response_text = vlm_client.send_message(messages, model_name)
                    successful_samples += 1

                    # Create a generic trace object that will work with our verifier
                    class GenericTrace:
                        def add_metadata(self, metadata):
                            logger.info(f"Weave tracing: {metadata}")

                    # Always use the generic trace to avoid type checking issues
                    trace = GenericTrace()

                    # Evaluate the response using the verifier
                    if prompt_type == "ranking":
                        from src.utils.db_schemas import RankingSampleData

                        ranking_sample = cast(RankingSampleData, sample)
                        evaluation = verifier.evaluate_ranking_response(
                            trace, ranking_sample, response_text
                        )
                    elif prompt_type in ["sanity_check", "interactive"]:
                        evaluation = verifier.evaluate_verification_response(
                            trace, sample, response_text
                        )
                    else:  # binary
                        evaluation = verifier.evaluate_binary_response(
                            trace, sample, response_text
                        )

                    # Store result
                    sample_result = {
                        "sample_id": sample_id,
                        "response": response_text,
                        "evaluation": evaluation,
                        "success": True,
                    }

                    results["samples"].append(sample_result)

                except Exception as e:
                    logger.error(f"Error sending sample {sample_id} to model: {e}")

                    # Log failure
                    sample_result = {
                        "sample_id": sample_id,
                        "error": str(e),
                        "success": False,
                    }
                    results["samples"].append(sample_result)

            except Exception as e:
                logger.warning(f"Failed to get sample {sample_id}: {e}")
                continue

    # Add summary metrics
    if successful_samples > 0:
        results["success_rate"] = successful_samples / total_samples

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = (
        output_dir / f"{prompt_type}_{model_name.replace('/', '_')}_{timestamp}.json"
    )
    result_file.parent.mkdir(parents=True, exist_ok=True)

    with open(result_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Saved results to {result_file}")

    return results


def main() -> None:
    """Main function for the evaluation pipeline."""
    # Initialize argument parser
    parser = ArgparseManager(description="PhysIQ VLM Evaluation Pipeline")
    parser.add_common_db_args()
    parser.add_evaluation_args()
    parser.add_weave_args()

    # Parse arguments
    args = parser.parse_args()

    # Validate and process arguments
    if args.iterations > 20:
        logger.warning("Limiting iterations to 20")
        args.iterations = 20

    # Set up evaluation types
    evaluation_types = args.evaluation_types
    if "all" in evaluation_types:
        evaluation_types = ["binary", "ranking", "sanity_check", "interactive"]

    # Initialize managers
    mongo_manager = MongoDBManager(db_name=args.db_name)
    dataset_manager = DatasetManager(db_manager=mongo_manager)

    # Initialize VLM client
    vlm_client = VLMClient()
    if not vlm_client.is_configured():
        logger.error(
            "OpenRouter API key not configured. Please set OPENROUTER_API_KEY environment variable."
        )
        return

    # Initialize Weave verifier
    verifier = WeaveVerifier(project_name=args.weave_project)

    # Check if models are valid
    valid_models = vlm_client.ALL_MODELS
    for model in args.models:
        if model not in valid_models:
            logger.warning(
                f"Model {model} is not in the list of known models. Available models:"
            )
            for provider, models in vlm_client.PROVIDERS.items():
                logger.warning(f"- {provider}: {', '.join(models)}")
            logger.warning("Continuing anyway, but this might cause errors.")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run evaluations
    template_range = range(args.start_template, args.stop_template + 1)

    for model_name in args.models:
        logger.info(f"Evaluating model: {model_name}")

        try:
            model_results = {}

            for eval_type in evaluation_types:
                logger.info(f"Running {eval_type} evaluation")

                # Create prompt manager for this evaluation type
                prompt_manager = PromptManager(prompt_type=eval_type)

                # Skip few-shot examples for interactive and confidence modes
                few_shot_count = (
                    0 if eval_type in ["interactive"] else args.few_shot_count
                )

                # Run evaluation with the verifier
                results = evaluate_model_on_samples(
                    model_name=model_name,
                    dataset_manager=dataset_manager,
                    prompt_manager=prompt_manager,
                    vlm_client=vlm_client,
                    verifier=verifier,
                    template_range=template_range,
                    iterations=args.iterations,
                    prompt_type=eval_type,
                    output_dir=output_dir,
                    few_shot_count=few_shot_count,
                    few_shot_frames=args.few_shot_frames,
                )

                model_results[eval_type] = results
                logger.info(f"Completed {eval_type} evaluation for {model_name}")

        except Exception as e:
            logger.error(f"Error evaluating model {model_name}: {e}")

    logger.info("Evaluation completed! Results saved to %s", output_dir)


if __name__ == "__main__":
    main()
