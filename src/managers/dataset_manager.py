import random
from pathlib import Path
from typing import Any

from loguru import logger

from src.utils.db_schemas import (
    FewShotData,
    ProposalSchema,
    PuzzleSchema,
    RankingFewShotData,
    RankingMetadata,
    RankingProposalItem,
    RankingSampleData,
    SampleData,
)

from .mongodb_manager import MongoDBManager


class DatasetManager:
    """
    This manager handles retrieval of puzzle data, proposals (correct or incorrect),
    and the associated screenshots. It also supports optional few-shot retrieval
    (i.e., extra puzzle+proposal pairs) to insert into a prompt as exemplars.
    """

    def __init__(
        self,
        db_manager: MongoDBManager | None,
        images_base_dir: str | Path = "images",
    ) -> None:
        """
        Args:
            db_manager: Instance of MongoDBManager.
            images_base_dir: The base directory where images are stored,
                             e.g. "images/" containing "correct_proposals/" etc.
        """
        self.db_manager = db_manager
        self.images_base_dir = Path(images_base_dir)

    def get_binary_sample(
        self,
        puzzle_id: str,
        num_frames: int,
        proposal_tier: str,
        few_shot_count: int = 0,
        few_shot_frames: int = 2,
    ) -> SampleData:
        """
        Retrieve a single puzzle + proposal and (optionally) a few-shot list of additional puzzles.

        Args:
            puzzle_id: The puzzle identifier, e.g. "00012:001"
            proposal_tier: Which tier of proposal to fetch. E.g. "CORRECT", "INCORRECT_EASY", etc.
            num_frames: Number of frames to retrieve: 2, 3, or 5.
                        (If only a single file is found, that single one is returned.)
            few_shot_count: 0 (no few-shot) or e.g. 2 or 4, indicating how many exemplars to pull.
            few_shot_frames: Number of frames to include for each few-shot example.

        Returns:
            A SampleData object containing the puzzle, proposal, images and optional few-shot examples.
        """
        # 1) Retrieve puzzle:
        puzzle = self.db_manager.get_puzzle_by_id(puzzle_id)
        if not puzzle:
            raise ValueError(f"No puzzle found with id={puzzle_id}")

        # 2) Retrieve a matching proposal (e.g. CORRECT or INCORRECT)
        proposal = self.db_manager.get_proposal(puzzle_id, proposal_tier)
        if not proposal:
            raise ValueError(
                f"No proposal found with puzzle_id={puzzle_id}, tier={proposal_tier}"
            )

        # 3) Locate screenshot images (path could be a file or a directory)
        images = self._retrieve_images(proposal.image_path, num_frames)

        # 4) Optionally retrieve few-shot exemplars, excluding the current puzzle
        few_shot_samples = []
        if few_shot_count > 0:
            few_shot_samples = self._get_few_shot_samples(
                few_shot_count, puzzle_id, few_shot_frames
            )

        return SampleData(
            puzzle=puzzle,
            proposal=proposal,
            images=images,
            few_shot=few_shot_samples,
        )

    def get_sanity_check_sample(
        self,
        puzzle_id: str,
        proposal_tier: str,
        few_shot_count: int = 0,
    ) -> SampleData:
        """
        Retrieve a single puzzle + proposal with only the last frame for sanity check prompts.

        Args:
            puzzle_id: The puzzle identifier, e.g. "00012:001"
            proposal_tier: Which tier of proposal to fetch. E.g. "CORRECT", "INCORRECT_EASY", etc.
            few_shot_count: 0 (no few-shot) or e.g. 2 or 4, indicating how many exemplars to pull.

        Returns:
            A SampleData object containing the puzzle, proposal, and last frame image.
        """
        # 1) Retrieve puzzle:
        puzzle = self.db_manager.get_puzzle_by_id(puzzle_id)
        if not puzzle:
            raise ValueError(f"No puzzle found with id={puzzle_id}")

        # 2) Retrieve a matching proposal (e.g. CORRECT or INCORRECT)
        proposal = self.db_manager.get_proposal(puzzle_id, proposal_tier)
        if not proposal:
            raise ValueError(
                f"No proposal found with puzzle_id={puzzle_id}, tier={proposal_tier}"
            )

        # 3) Locate only the last screenshot image
        images = self._retrieve_last_frame(proposal.image_path)

        # 4) Optionally retrieve few-shot exemplars, excluding the current puzzle
        few_shot_samples = []
        if few_shot_count > 0:
            few_shot_samples = self._get_few_shot_samples_last_frame(
                few_shot_count, puzzle_id
            )

        return SampleData(
            puzzle=puzzle,
            proposal=proposal,
            images=images,
            few_shot=few_shot_samples,
        )

    def get_ranking_sample(
        self,
        puzzle_id: str,
        num_frames: int,
        few_shot_count: int = 0,
    ) -> RankingSampleData:
        """
        Retrieve a puzzle and all its proposals (correct, incorrect_easy, medium, hard)
        for a ranking task, with random ordering of proposals.

        Args:
            puzzle_id: The puzzle identifier, e.g. "00012:001"
            num_frames: Number of frames to retrieve for each proposal
            few_shot_count: Number of few-shot examples to include
            few_shot_frames: Number of frames to include for each few-shot example

        Returns:
            A RankingSampleData object containing the puzzle and multiple proposals
        """
        # Define correct ranking order: CORRECT > INCORRECT_HARD > INCORRECT_MEDIUM > INCORRECT_EASY
        ranking_order = {
            "CORRECT": 0,
            "INCORRECT_HARD": 1,
            "INCORRECT_MEDIUM": 2,
            "INCORRECT_EASY": 3,
        }

        # 1) Retrieve puzzle
        puzzle = self.db_manager.get_puzzle_by_id(puzzle_id)
        if not puzzle:
            raise ValueError(f"No puzzle found with id={puzzle_id}")

        # 2) Retrieve all proposal tiers for this puzzle
        proposal_tiers = [
            "CORRECT",
            "INCORRECT_EASY",
            "INCORRECT_MEDIUM",
            "INCORRECT_HARD",
        ]

        proposals = []
        images_list = []
        tiers_list = []  # Store the tier for each proposal

        for tier_index, tier in enumerate(proposal_tiers):
            proposal = self.db_manager.get_proposal(puzzle_id, tier)
            if proposal:
                # Get images for this proposal
                images = self._retrieve_images(proposal.image_path, num_frames)
                if images:
                    proposals.append(proposal)
                    images_list.append(images)
                    tiers_list.append(tier)

        if not proposals:
            raise ValueError(f"No valid proposals found for puzzle_id={puzzle_id}")

        # Randomize the order while keeping track of which proposal is which
        indices = list(range(len(proposals)))
        combined = list(zip(indices, proposals, images_list, tiers_list))
        random.shuffle(combined)

        # Extract the shuffled data
        shuffled_indices, shuffled_proposals, shuffled_images_list, shuffled_tiers = (
            zip(*combined)
        )

        # Store the correct answer order based on the ranking_order dictionary
        # Higher ranked proposals (lower ranking_order value) should come first
        correct_ranking = []
        for i, tier in enumerate(shuffled_tiers):
            # Each position stores the position number of the proposal in order of correctness
            rank_position = ranking_order.get(
                tier, 4
            )  # Default to lowest rank if unknown
            correct_ranking.append((i, rank_position))

        # Sort by rank position and extract the indices
        correct_ranking.sort(key=lambda x: x[1])
        correct_ranking = [idx for idx, _ in correct_ranking]

        # 3) Get few-shot examples if requested
        few_shot_samples = []
        if few_shot_count > 0:
            few_shot_samples = self._get_ranking_few_shot_samples(
                few_shot_count, puzzle_id
            )

        # Create a list of RankingProposalItem objects
        ranking_proposals = [
            RankingProposalItem(
                proposal=prop, images=imgs, tier=tier, original_index=idx
            )
            for idx, prop, imgs, tier in zip(
                shuffled_indices,
                shuffled_proposals,
                shuffled_images_list,
                shuffled_tiers,
            )
        ]

        # Create metadata
        ranking_metadata = RankingMetadata(
            correct_ranking=correct_ranking, proposal_tiers=shuffled_tiers  # type: ignore
        )

        # Return using the first proposal for backward compatibility with standard SampleData fields
        return RankingSampleData(
            puzzle=puzzle,
            proposal=shuffled_proposals[
                0
            ],  # Using first as primary (for compatibility)
            images=shuffled_images_list[
                0
            ],  # Using first as primary (for compatibility)
            few_shot=few_shot_samples,  # type: ignore
            proposals=ranking_proposals,
            metadata=ranking_metadata,
        )

    def get_interactive_sample(
        self,
        puzzle_id: str,
    ) -> SampleData:
        """
        Retrieve a puzzle for interactive solving, showing only the initial state without proposals.

        Args:
            puzzle_id: The puzzle identifier, e.g. "00012:001"

        Returns:
            A SampleData object containing the puzzle and its base image.
        """
        # 1) Retrieve puzzle
        puzzle = self.db_manager.get_puzzle_by_id(puzzle_id)
        if not puzzle:
            raise ValueError(f"No puzzle found with id={puzzle_id}")

        # For interactive prompts, we need the original puzzle image without proposals
        images = []
        if puzzle.image_path:
            image_path = Path(puzzle.image_path)
            if image_path.exists():
                images = [str(image_path)]
            else:
                # Try with base directory prefix
                full_path = self.images_base_dir / image_path
                if full_path.exists():
                    images = [str(full_path)]
                else:
                    logger.warning(
                        f"Puzzle image not found at {image_path} or {full_path}"
                    )

        if not images:
            logger.warning(
                f"No image found for puzzle {puzzle_id}, using CORRECT proposal instead"
            )
            # Fall back to using the first frame of a CORRECT proposal if puzzle image isn't available
            proposal = self.db_manager.get_proposal(puzzle_id, "CORRECT")
            if proposal:
                images = self._retrieve_images(proposal.image_path, 1)
            else:
                raise ValueError(f"No images available for puzzle {puzzle_id}")

        # Since we only need the puzzle, we'll use a placeholder proposal
        # The UI will ignore this for interactive prompts
        placeholder_proposal = self.db_manager.get_proposal(puzzle_id, "CORRECT")
        if not placeholder_proposal:
            # If no CORRECT proposal exists, just use any available proposal
            proposals = list(
                self.db_manager.db["proposals"].find({"id": puzzle_id}).limit(1)
            )
            if proposals:
                placeholder_proposal = ProposalSchema(**proposals[0])
            else:
                raise ValueError(f"No proposals found for puzzle_id={puzzle_id}")

        return SampleData(
            puzzle=puzzle,
            proposal=placeholder_proposal,
            images=images,
            few_shot=None,  # No few-shot for interactive mode
        )

    def _get_ranking_few_shot_samples(
        self, few_shot_count: int, current_puzzle_id: str
    ) -> list[RankingFewShotData]:
        """
        Create few-shot examples specifically for ranking tasks.
        Each few-shot example contains multiple proposals for a single puzzle.

        Args:
            few_shot_count: Number of few-shot puzzles to retrieve
            current_puzzle_id: Current puzzle ID to exclude
            few_shot_frames: Number of frames per proposal (always using first frame for ranking)

        Returns:
            List of RankingFewShotData objects with ranking examples
        """
        # Define correct ranking order: CORRECT > INCORRECT_HARD > INCORRECT_MEDIUM > INCORRECT_EASY
        ranking_order = {
            "CORRECT": 0,
            "INCORRECT_HARD": 1,
            "INCORRECT_MEDIUM": 2,
            "INCORRECT_EASY": 3,
        }

        if few_shot_count <= 0:
            return []

        # Get unique puzzle IDs (excluding current)
        base_filter = {}
        if current_puzzle_id:
            base_filter = {"id": {"$ne": current_puzzle_id}}

        # Find puzzles that have all proposal types
        puzzles_with_proposals = {}
        proposal_tiers = [
            "CORRECT",
            "INCORRECT_EASY",
            "INCORRECT_MEDIUM",
            "INCORRECT_HARD",
        ]

        # First, get all puzzles
        puzzle_cursor = self.db_manager.db["puzzles"].find(base_filter)

        for puzzle_doc in puzzle_cursor:
            puzzle_id = puzzle_doc["id"]
            has_all_tiers = True

            # Check if this puzzle has all proposal tiers
            for tier in proposal_tiers:
                proposal = self.db_manager.db["proposals"].find_one(
                    {"id": puzzle_id, "tier": tier}
                )
                if not proposal:
                    has_all_tiers = False
                    break

            if has_all_tiers:
                puzzles_with_proposals[puzzle_id] = puzzle_doc

        # Pick random puzzles from those with all proposals
        puzzle_ids = list(puzzles_with_proposals.keys())
        if not puzzle_ids:
            logger.warning(
                "No puzzles found with all proposal tiers for few-shot examples"
            )
            return []

        # Select random puzzles
        few_shot_puzzle_ids = random.sample(
            puzzle_ids, min(few_shot_count, len(puzzle_ids))
        )

        few_shot_data = []
        for idx, fs_puzzle_id in enumerate(few_shot_puzzle_ids):
            puzzle_doc = puzzles_with_proposals[fs_puzzle_id]
            puzzle = PuzzleSchema(**puzzle_doc)

            # For each puzzle, get all proposals and randomize their order
            fs_proposals = []
            fs_images_list = []
            fs_tiers = []

            # Ensure we have all proposals for this puzzle
            all_proposals_found = True
            for tier in proposal_tiers:
                proposal_doc = self.db_manager.db["proposals"].find_one(
                    {"id": fs_puzzle_id, "tier": tier}
                )
                if proposal_doc:
                    proposal = ProposalSchema(**proposal_doc)
                    # For ranking, always use first frame only
                    images = self._retrieve_images(proposal.image_path, 1)
                    if images:
                        fs_proposals.append(proposal)
                        fs_images_list.append(images)
                        fs_tiers.append(tier)
                else:
                    all_proposals_found = False
                    break

            # Skip this puzzle if we're missing any proposal tier
            if not all_proposals_found or len(fs_proposals) != len(proposal_tiers):
                logger.warning(
                    f"Skipping puzzle {fs_puzzle_id} - missing some proposal tiers"
                )
                continue

            # Randomize order while keeping track of index positions
            indices = list(range(len(fs_proposals)))
            combined = list(zip(indices, fs_proposals, fs_images_list, fs_tiers))
            random.shuffle(combined)

            (
                shuffled_indices,
                shuffled_proposals,
                shuffled_images_list,
                shuffled_tiers,
            ) = zip(*combined)

            # Create correct ranking based on tier quality (sort by ranking_order values)
            # First, create pairs of (index, rank_position) where lower rank_position is better
            correct_ranking_pairs = []
            for i, tier in enumerate(shuffled_tiers):
                rank_position = ranking_order.get(tier, 4)
                correct_ranking_pairs.append((i, rank_position))

            # Sort by rank position (second element of tuple)
            correct_ranking_pairs.sort(key=lambda x: x[1])

            # Extract just the indices in order from best to worst
            correct_ranking = [idx for idx, _ in correct_ranking_pairs]

            # Create ranking metadata
            ranking_metadata = RankingMetadata(
                correct_ranking=correct_ranking,
                proposal_tiers=list(shuffled_tiers),  # Convert tuple to list
            )

            # Create RankingFewShotData object instead of FewShotData
            few_shot = RankingFewShotData(
                puzzle=puzzle,
                proposal=shuffled_proposals[0],  # First proposal for compatibility
                images=shuffled_images_list[0],  # First images for compatibility
                index=idx + 1,
                proposals=list(shuffled_proposals),  # Convert tuple to list
                images_list=list(shuffled_images_list),  # Convert tuple to list
                metadata=ranking_metadata,
            )

            # Logging to confirm structure
            logger.debug(
                f"Created ranking few-shot example {idx+1}: "
                f"{len(few_shot.proposals)} proposals, "
                f"correct ranking: {correct_ranking}"
            )

            few_shot_data.append(few_shot)

        return few_shot_data

    def _retrieve_images(self, image_path: str, num_frames: int) -> list[str]:
        """
        Given an 'image_path' which might be a single .png file or a directory,
        return the selected frames (first, middle, last, etc.).

        Args:
            image_path: Path as stored in proposals.image_path (could be "images/correct_proposals/00012_001/1.png")
            num_frames: 2 (start/end), 3, or 5, etc.

        Returns:
            A list of absolute or relative file paths (as strings) to the chosen screenshots.
        """
        p = Path(image_path)
        if p.is_file():
            # There's only one file, so we just return that
            return [str(p)]

        if not p.is_dir():
            # Try to see if it's relative to base dir
            possible_dir = self.images_base_dir / p
            if possible_dir.is_dir():
                p = possible_dir
            else:
                logger.warning(
                    f"Image path '{image_path}' is neither file nor dir. Returning empty list."
                )
                return []

        # Now 'p' is a directory. Let's get all .png inside, sorted
        all_images = sorted(p.glob("*.png"), key=lambda x: x.name)
        if not all_images:
            logger.warning(f"No .png files found in folder {p}")
            return []

        if num_frames <= 1:
            # If user mistakenly sets 1 or 0
            return [str(all_images[0])]

        if len(all_images) <= num_frames:
            # If the folder has fewer images than we want, just return them all
            return [str(x) for x in all_images]

        # Otherwise, pick frames from start, middle, end
        indices = self.compute_frame_indices(len(all_images), num_frames)
        all_images = sorted(all_images, key=lambda x: int(x.stem))
        logger.debug(
            f"Selected indices: {indices}\tNumber of images: {len(all_images)}"
        )
        selected = [all_images[i] for i in indices]
        return [str(s) for s in selected]

    def _retrieve_last_frame(self, image_path: str) -> list[str]:
        """
        Given an 'image_path', retrieve only the last frame.

        Args:
            image_path: Path as stored in proposals.image_path

        Returns:
            A list containing only the path to the last frame
        """
        p = Path(image_path)
        if p.is_file():
            # There's only one file, so we just return that
            return [str(p)]

        if not p.is_dir():
            # Try to see if it's relative to base dir
            possible_dir = self.images_base_dir / p
            if possible_dir.is_dir():
                p = possible_dir
            else:
                logger.warning(
                    f"Image path '{image_path}' is neither file nor dir. Returning empty list."
                )
                return []

        # Now 'p' is a directory. Let's get all .png inside, sorted
        all_images = sorted(p.glob("*.png"), key=lambda x: int(x.stem))
        if not all_images:
            logger.warning(f"No .png files found in folder {p}")
            return []

        # Return only the last image
        return [str(all_images[-1])]

    def compute_frame_indices(self, total: int, num_frames: int) -> list[int]:
        """
        Utility for picking (start, middle..., end) frames from a list of length 'total'.
        E.g. if total=10, num_frames=3 => [0, 4, 9]
        """
        assert num_frames >= 1 and num_frames <= 5, "num_frames must be greater than 1"
        assert total >= num_frames, "total must be greater than num_frames"
        if num_frames == 2:
            indices = [0, total - 1]
        # For 3 or 5 frames, we basically spread them out evenly
        elif num_frames == 3:
            # start, mid, end
            indices = [0, total // 2, total - 1]
        elif num_frames == 4:
            indices = [0, total // 3, 2 * total // 3, total - 1]
        else:
            indices = [
                0,
                total // 4,
                total // 2,
                3 * total // 4,
                total - 1,
            ]
        return indices

    def _get_few_shot_samples(
        self, few_shot_count: int, current_puzzle_id: str, few_shot_frames: int = 2
    ) -> list[FewShotData]:
        """
        Retrieve a random selection of puzzle+proposal+images for few-shot usage.
        Ensures a mix of correct and incorrect examples, excluding the current puzzle.

        Args:
            few_shot_count: Number of few-shot examples to retrieve
            current_puzzle_id: ID of the current puzzle to exclude from examples
            few_shot_frames: Number of frames to include for each few-shot example.

        Returns:
            List of FewShotData objects
        """
        if few_shot_count <= 0:
            return []

        # Make sure we have both CORRECT and INCORRECT examples
        half = few_shot_count // 2
        remainder = few_shot_count - half

        all_docs = []

        # Build the base exclusion filter
        base_filter = {}
        if current_puzzle_id:
            base_filter = {"id": {"$ne": current_puzzle_id}}

        # Grab CORRECT examples (typically "Yes" answers)
        if half > 0:
            correct_filter = {"tier": "CORRECT"}
            correct_filter.update(base_filter)  # type: ignore

            correct_cursor = self.db_manager.db["proposals"].aggregate(
                [{"$match": correct_filter}, {"$sample": {"size": half}}]
            )
            all_docs.extend(list(correct_cursor))

        # Grab INCORRECT examples (typically "No" answers)
        if remainder > 0:
            incorrect_filter = {"tier": {"$regex": "^INCORRECT"}}
            incorrect_filter.update(base_filter)

            incorrect_cursor = self.db_manager.db["proposals"].aggregate(
                [{"$match": incorrect_filter}, {"$sample": {"size": remainder}}]
            )
            all_docs.extend(list(incorrect_cursor))

        random.shuffle(all_docs)

        few_shot_data = []
        for doc in all_docs:
            puzzle_id = doc["id"]
            puzzle_doc = self.db_manager.db["puzzles"].find_one({"id": puzzle_id})
            if not puzzle_doc:
                logger.warning(f"Could not find puzzle with ID {puzzle_id}")
                continue

            images = self._retrieve_images(doc["image_path"], few_shot_frames)
            few_shot_data.append(
                FewShotData(
                    puzzle=PuzzleSchema(**puzzle_doc),
                    proposal=ProposalSchema(**doc),
                    images=images,
                    index=len(few_shot_data) + 1,
                )
            )

        return few_shot_data

    def _get_few_shot_samples_last_frame(
        self, few_shot_count: int, current_puzzle_id: str
    ) -> list[FewShotData]:
        """
        Retrieve a random selection of puzzle+proposal+last_frame for few-shot usage.

        Args:
            few_shot_count: Number of few-shot examples to retrieve
            current_puzzle_id: ID of the current puzzle to exclude from examples

        Returns:
            List of FewShotData objects with only the last frame
        """
        if few_shot_count <= 0:
            return []

        # Make sure we have both CORRECT and INCORRECT examples
        half = few_shot_count // 2
        remainder = few_shot_count - half

        all_docs = []

        # Build the base exclusion filter
        base_filter = {}
        if current_puzzle_id:
            base_filter = {"id": {"$ne": current_puzzle_id}}

        # Grab CORRECT examples (typically "Yes" answers)
        if half > 0:
            correct_filter = {"tier": "CORRECT"}
            correct_filter.update(base_filter)  # type: ignore

            correct_cursor = self.db_manager.db["proposals"].aggregate(
                [{"$match": correct_filter}, {"$sample": {"size": half}}]
            )
            all_docs.extend(list(correct_cursor))

        # Grab INCORRECT examples (typically "No" answers)
        if remainder > 0:
            incorrect_filter = {"tier": {"$regex": "^INCORRECT"}}
            incorrect_filter.update(base_filter)

            incorrect_cursor = self.db_manager.db["proposals"].aggregate(
                [{"$match": incorrect_filter}, {"$sample": {"size": remainder}}]
            )
            all_docs.extend(list(incorrect_cursor))

        random.shuffle(all_docs)

        few_shot_data = []
        for doc in all_docs:
            puzzle_id = doc["id"]
            puzzle_doc = self.db_manager.db["puzzles"].find_one({"id": puzzle_id})
            if not puzzle_doc:
                logger.warning(f"Could not find puzzle with ID {puzzle_id}")
                continue

            # Get only the last frame for each few-shot example
            images = self._retrieve_last_frame(doc["image_path"])
            few_shot_data.append(
                FewShotData(
                    puzzle=PuzzleSchema(**puzzle_doc),
                    proposal=ProposalSchema(**doc),
                    images=images,
                    index=len(few_shot_data) + 1,
                )
            )

        return few_shot_data
