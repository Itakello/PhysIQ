from typing import Any, Dict, List

import weave
from loguru import logger

from src.utils.db_schemas import RankingSampleData, SampleData


class WeaveVerifier:
    """
    A verifier class that uses Weave to track and evaluate model responses
    for different types of physics reasoning tasks.
    """

    def __init__(self, project_name: str = "physiq-evaluations") -> None:
        """
        Initialize the WeaveVerifier.

        Args:
            project_name: The name of the Weave project (used as a tag)
        """
        self.project_name = project_name
        # We'll tag our evaluations with this project name

    def evaluate_binary_response(
        self, trace: Any, sample: SampleData, response: str
    ) -> Dict[str, Any]:
        """
        Evaluate a binary response (correct/incorrect solution).

        Args:
            trace: The Weave trace from the model call
            sample: The sample data containing ground truth information
            response: The model's response text

        Returns:
            A dictionary with evaluation results
        """
        # Get the ground truth from the sample
        ground_truth = sample.proposal.tier

        # Parse response to determine if model thought the solution was correct
        # This requires analyzing the model's response
        if "correct" in response.lower():
            prediction = "CORRECT"
        elif "incorrect" in response.lower():
            prediction = "INCORRECT"
        else:
            prediction = "UNCLEAR"

        # Calculate accuracy
        is_correct = (
            prediction == "CORRECT"
            and ground_truth == "CORRECT"
            or prediction == "INCORRECT"
            and "INCORRECT" in ground_truth
        )

        # Record evaluation result
        result = {
            "ground_truth": ground_truth,
            "prediction": prediction,
            "is_correct": is_correct,
            "accuracy": 1.0 if is_correct else 0.0,
        }

        # Log the result to the Weave trace
        try:
            if hasattr(trace, "add_metadata"):
                trace.add_metadata({"evaluation_result": result})
        except Exception as e:
            logger.warning(f"Failed to add metadata to trace: {e}")

        # Create an evaluation in Weave
        try:
            # Skip direct usage of Weave API due to compatibility issues
            logger.info(f"Binary evaluation result for {sample.puzzle.id}: {result}")
        except Exception as e:
            logger.warning(f"Failed to create Weave evaluation: {e}")

        return result

    def evaluate_ranking_response(
        self, trace: Any, sample: RankingSampleData, response: str
    ) -> Dict[str, Any]:
        """
        Evaluate a ranking response (ordering solutions by correctness).

        Args:
            trace: The Weave trace from the model call
            sample: The ranking sample data containing ground truth information
            response: The model's response text

        Returns:
            A dictionary with evaluation results
        """
        # Get the ground truth ranking from the sample
        correct_ranking = sample.metadata.correct_ranking

        # Parse response to extract the model's ranking
        # This will depend on the format we expect from the model
        # For this example, we'll assume the model outputs a list of indices
        try:
            # This is just a placeholder for actual parsing logic
            # Real implementation would extract the ranking from the response text
            predicted_ranking = self._parse_ranking_from_response(
                response, len(correct_ranking)
            )

            # Calculate accuracy (1.0 if completely correct, 0.0 if completely wrong)
            is_correct = predicted_ranking == correct_ranking

            # Calculate partial correctness (e.g., Kendall Tau correlation)
            # This would require a proper implementation
            correlation = self._calculate_ranking_correlation(
                correct_ranking, predicted_ranking
            )

            result = {
                "ground_truth": correct_ranking,
                "prediction": predicted_ranking,
                "is_exact_match": is_correct,
                "correlation": correlation,
                "accuracy": 1.0 if is_correct else correlation,
            }
        except Exception as e:
            logger.error(f"Error parsing ranking from response: {e}")
            result = {
                "ground_truth": correct_ranking,
                "prediction": None,
                "is_exact_match": False,
                "correlation": 0.0,
                "accuracy": 0.0,
                "error": str(e),
            }

        # Log the result to the Weave trace
        try:
            if hasattr(trace, "add_metadata"):
                trace.add_metadata({"evaluation_result": result})
        except Exception as e:
            logger.warning(f"Failed to add metadata to trace: {e}")

        # Create an evaluation in Weave
        try:
            # Skip direct usage of Weave API due to compatibility issues
            logger.info(f"Ranking evaluation result for {sample.puzzle.id}: {result}")
        except Exception as e:
            logger.warning(f"Failed to create Weave evaluation: {e}")

        return result

    def evaluate_verification_response(
        self, trace: Any, sample: SampleData, response: str
    ) -> Dict[str, Any]:
        """
        Evaluate a verification/sanity check response.

        Args:
            trace: The Weave trace from the model call
            sample: The sample data containing ground truth information
            response: The model's response text

        Returns:
            A dictionary with evaluation results
        """
        # For sanity checks, we expect the model to recognize when a task is correct
        ground_truth = sample.proposal.tier

        # Parse response
        if "correct" in response.lower():
            prediction = "CORRECT"
        elif "incorrect" in response.lower():
            prediction = "INCORRECT"
        else:
            prediction = "UNCLEAR"

        # Calculate accuracy
        is_correct = prediction == ground_truth

        # Record evaluation result
        result = {
            "ground_truth": ground_truth,
            "prediction": prediction,
            "is_correct": is_correct,
            "accuracy": 1.0 if is_correct else 0.0,
        }

        # Log the result to the Weave trace
        try:
            if hasattr(trace, "add_metadata"):
                trace.add_metadata({"evaluation_result": result})
        except Exception as e:
            logger.warning(f"Failed to add metadata to trace: {e}")

        # Create an evaluation in Weave
        try:
            # Skip direct usage of Weave API due to compatibility issues
            logger.info(
                f"Verification evaluation result for {sample.puzzle.id}: {result}"
            )
        except Exception as e:
            logger.warning(f"Failed to create Weave evaluation: {e}")

        return result

    def _parse_ranking_from_response(
        self, response: str, num_proposals: int
    ) -> List[int]:
        """
        Parse a ranking from a model's response text.

        Args:
            response: The response text to parse
            num_proposals: The number of proposals that should be ranked

        Returns:
            A list of integers representing the ranking
        """
        # This is a placeholder - actual implementation would depend on
        # the expected format of model responses
        # For example, extracting a list of numbers from text

        # For now, just return a dummy ranking
        return list(range(num_proposals))

    def _calculate_ranking_correlation(
        self, ground_truth: List[int], prediction: List[int]
    ) -> float:
        """
        Calculate a correlation coefficient between two rankings.

        Args:
            ground_truth: The ground truth ranking
            prediction: The predicted ranking

        Returns:
            A correlation coefficient between 0.0 and 1.0
        """
        # This is a placeholder - actual implementation could use
        # Kendall's Tau or other ranking correlation metrics

        # For now, just return a simple similarity score
        if len(ground_truth) != len(prediction):
            return 0.0

        correct_positions = sum(1 for i, j in zip(ground_truth, prediction) if i == j)
        return correct_positions / len(ground_truth)
