import base64
import inspect
import os
import pprint
from typing import Any, List, Literal, TypedDict, Union

import streamlit as st
from loguru import logger

from src.evaluation.interactive_eval import (
    evaluate_interactive_response,
    generate_feedback_message,
)
from src.managers import DatasetManager, MongoDBManager, PromptManager
from src.utils.vlm_client import VLMClient


# Define more specific types for OpenAI message content
class ImageUrlDict(TypedDict):
    url: str
    detail: str


class TextContent(TypedDict):
    type: Literal["text"]
    text: str


class ImageUrlContent(TypedDict):
    type: Literal["image_url"]
    image_url: ImageUrlDict


# Define a type for the image_url structure
ContentItem = Union[TextContent, ImageUrlContent]
MessageContent = Union[str, List[ContentItem]]


def display_image(container, image_url: str) -> None:
    """
    Helper function to display images with consistent sizing

    Args:
        container: Streamlit container or column to display the image in
        image_url: Path to image file or base64 encoded image data
    """
    width = 200  # Fixed width of 200px

    try:
        if image_url.startswith("data:image/png;base64,"):
            # For base64 encoded images
            container.markdown(
                f'<img src="{image_url}" style="width:{width}px;">',
                unsafe_allow_html=True,
            )
        else:
            # For file path images
            if os.path.isfile(image_url):
                container.image(image_url, width=width)
            else:
                logger.error(f"Image file not found: {image_url}")
                container.error("Image file not found")
    except Exception as e:
        logger.error(f"Failed to display image: {e}")
        container.error(f"Failed to load image: {str(e)}")


def display_conversation_history(
    messages, interactive_messages, show_raw_messages=False
):
    """Display the full conversation history including original messages and interactive messages"""
    # First display the original system and user messages
    if messages:
        # Always display the system message first
        render_message(messages[0])
        if show_raw_messages:
            with st.expander(f"Raw message: {messages[0].get('role')}", expanded=True):
                display_raw_message(st, messages[0])

        # Then display the initial user message
        if len(messages) > 1:
            render_message(messages[1])
            if show_raw_messages:
                with st.expander(
                    f"Raw message: {messages[1].get('role')}", expanded=True
                ):
                    display_raw_message(st, messages[1])

    # Then display all the interactive messages
    for msg in interactive_messages:
        render_message(msg)
        if show_raw_messages:
            with st.expander(f"Raw message: {msg.get('role')}", expanded=True):
                display_raw_message(st, msg)


def render_message(message: dict[str, Any]) -> None:
    """Render a single message in the Streamlit chat interface"""
    role = message.get("role", "system")
    content = message.get("content", "")

    with st.chat_message(role):
        # Handle different content types
        if isinstance(content, str):
            st.write(content)
        elif isinstance(content, list):
            # Process items while grouping consecutive images
            i = 0
            while i < len(content):
                item = content[i]

                if item["type"] == "text":
                    # Render text items individually
                    st.write(item["text"])
                    i += 1
                elif item["type"] == "image_url":
                    # Find consecutive image items
                    consecutive_images = [item]
                    next_idx = i + 1

                    while (
                        next_idx < len(content)
                        and content[next_idx]["type"] == "image_url"
                    ):
                        consecutive_images.append(content[next_idx])
                        next_idx += 1

                    # Create columns for multiple images
                    if len(consecutive_images) > 1:
                        cols = st.columns(len(consecutive_images))
                        for col_idx, img_item in enumerate(consecutive_images):
                            image_url = img_item["image_url"]["url"]
                            display_image(cols[col_idx], image_url)
                    else:
                        # Single image
                        image_url = item["image_url"]["url"]
                        display_image(st, image_url)

                    # Move index past all consumed images
                    i = next_idx
                else:
                    # Unknown type, skip
                    i += 1


def display_raw_message(container, message: dict[str, Any]) -> None:
    """Display the raw message structure for debugging"""
    # Create a deep copy to avoid modifying the original message
    display_msg = message.copy()

    # Handle base64 image data for better display
    if isinstance(display_msg.get("content"), list):
        content_copy = []
        for item in display_msg.get("content", []):
            item_copy = item.copy()
            if item_copy.get("type") == "image_url" and "image_url" in item_copy:
                # Replace base64 data with placeholder
                image_url_copy = item_copy["image_url"].copy()
                if "url" in image_url_copy and image_url_copy["url"].startswith(
                    "data:image"
                ):
                    image_url_copy["url"] = "data:image/png;base64,[BASE64_DATA]"
                item_copy["image_url"] = image_url_copy
            content_copy.append(item_copy)
        display_msg["content"] = content_copy

    container.json(display_msg)


def display_ranking_info(container, sample) -> None:
    """Display ranking-specific information about proposals and their scores"""
    if hasattr(sample, "proposals") and hasattr(sample, "metadata"):
        container.subheader("Ranking Information")

        # Create table headers
        cols = container.columns([1, 2, 2, 2])
        cols[0].markdown("**Position**")
        cols[1].markdown("**Proposal Tier**")
        cols[2].markdown("**Original Index**")
        cols[3].markdown("**Expected Rank**")

        # Create table rows
        for i, proposal_item in enumerate(sample.proposals):
            cols = container.columns([1, 2, 2, 2])
            cols[0].write(f"{i+1}")
            cols[1].write(proposal_item.tier)
            cols[2].write(f"{proposal_item.original_index}")

            # Find expected rank (position in correct_ranking)
            expected_rank = "Unknown"
            if hasattr(sample.metadata, "correct_ranking"):
                for pos, idx in enumerate(sample.metadata.correct_ranking):
                    if idx == proposal_item.original_index:
                        expected_rank = f"{pos+1}"
                        break

            cols[3].write(expected_rank)

        # Additional information about correct ordering
        container.write("**Correct ordering (from best to worst):**")
        if hasattr(sample.metadata, "proposal_tiers"):
            tiers = sample.metadata.proposal_tiers
            ranking_indices = list(range(len(tiers)))

            # Sort ranking indices by expected correctness (CORRECT first, then INCORRECT tiers)
            ranking_indices.sort(
                key=lambda i: (
                    0
                    if tiers[i] == "CORRECT"
                    else (
                        1
                        if tiers[i] == "INCORRECT_EASY"
                        else 2 if tiers[i] == "INCORRECT_MEDIUM" else 3
                    )
                )
            )

            # Show the correct order using 1-based indexing
            correct_order = [idx + 1 for idx in ranking_indices]
            container.write(f"Proposals: {correct_order}")
    else:
        container.warning("This is not a properly formatted ranking sample")


def select_representative_frames(
    screenshots: list[str], max_frames: int = 5
) -> list[str]:
    """
    Select representative frames from a list of screenshots using the same logic as
    compute_frame_indices in the DatasetManager.

    Args:
        screenshots: List of screenshot file paths
        max_frames: Maximum number of frames to select (default: 5)

    Returns:
        List of selected screenshot file paths
    """
    total = len(screenshots)

    # If we have fewer screenshots than the max, return all of them
    if total <= max_frames:
        return screenshots

    # Otherwise, select representative frames (start, middle, end, etc.)
    # This replicates the logic from DatasetManager.compute_frame_indices
    if max_frames == 2:
        indices = [0, total - 1]
    elif max_frames == 3:
        # start, mid, end
        indices = [0, total // 2, total - 1]
    elif max_frames == 4:
        indices = [0, total // 3, 2 * total // 3, total - 1]
    else:  # max_frames == 5 or more
        indices = [
            0,
            total // 4,
            total // 2,
            3 * total // 4,
            total - 1,
        ]

    return [screenshots[i] for i in indices]


def display_interactive_evaluation(
    response: str, puzzle: dict, attempt_number: int = 1
) -> tuple[str, list | None, str]:
    """
    Evaluate an interactive response including simulation results without displaying feedback.

    Args:
        response: The LLM's response text
        puzzle: The puzzle definition
        attempt_number: Current attempt number (1-5)

    Returns:
        Tuple of (status, screenshots or None, feedback message)
    """
    # Call the evaluation function with more screenshots than we'll display
    # to get better coverage of the simulation
    result = evaluate_interactive_response(
        response=response,
        puzzle=puzzle,
        visualize=False,  # No visual window needed in Streamlit
        num_screenshots=10,  # Capture more screenshots during simulation for better coverage
    )

    # Process screenshots
    screenshots = []
    if result.screenshots:
        # Filter only valid screenshot file paths
        screenshots = [
            path
            for path in result.screenshots
            if isinstance(path, str) and os.path.isfile(path)
        ]

        if screenshots:
            # Select representative frames (max 5)
            screenshots = select_representative_frames(screenshots, max_frames=5)
        else:
            logger.warning("No valid screenshots were generated during simulation")
    else:
        logger.warning("No screenshots were generated during simulation")

    # Generate the feedback message for the next turn
    feedback = generate_feedback_message(result.status, attempt_number)

    # Remove any <CURRENT_CURSOR_POSITION> markers that might be in the feedback
    feedback = feedback.replace("<CURRENT_CURSOR_POSITION>", "")

    # Debug: Print the feedback message
    print(f"DEBUG - Feedback message: {feedback}")
    if "[IMAGES]" in feedback:
        parts = feedback.split("[IMAGES]")
        print(f"DEBUG - First part: {parts[0]}")
        print(f"DEBUG - Second part: {parts[1]}")

    return result.status, screenshots, feedback


def main() -> None:
    st.set_page_config(
        page_title="PhysIQ Prompt Tester",
        page_icon="🧠",
        layout="wide",
    )

    st.title("PhysIQ Prompt Visualizer")
    st.write("Visualize the prompts generated for the PhysIQ physics simulation task.")

    # Initialize VLM client
    vlm_client = VLMClient()

    # Sidebar configuration
    st.sidebar.title("Configuration")

    # Add debug mode toggle in sidebar
    debug_mode = st.sidebar.checkbox("Enable Debug Mode", value=False)

    # Create a container for debug output that we'll use later
    debug_container = st.container()

    # Initialize a dictionary to store debug variables
    if "debug_vars" not in st.session_state:
        st.session_state.debug_vars = {}

    # Helper function to add variables to debug tracking
    def debug_track(name, value):
        if debug_mode:
            st.session_state.debug_vars[name] = value
        return value

    # Initialize database managers
    try:
        # Initialize managers
        mongo_manager = MongoDBManager(db_name="physiq_db")
        dataset_manager = DatasetManager(db_manager=mongo_manager)

        # Fetch all correct proposals to populate the dropdowns
        with st.spinner("Fetching available puzzles..."):
            correct_proposals = mongo_manager.get_all_correct_proposals()

            # Extract unique template IDs and iteration IDs
            template_ids = sorted({int(p.id.split(":")[0]) for p in correct_proposals})

        prompt_type = st.sidebar.selectbox(
            "Prompt Type",
            options=["sanity_check", "ranking", "binary", "confidence", "interactive"],
            index=4,
        )

        # Template ID selection
        selected_template = st.sidebar.selectbox(
            "Template ID",
            options=template_ids,
            index=0,
            format_func=lambda x: f"{x:05d}",
        )

        # Filter iterations for the selected template
        template_proposals = [
            p for p in correct_proposals if int(p.id.split(":")[0]) == selected_template
        ]
        iteration_ids = sorted({int(p.id.split(":")[1]) for p in template_proposals})

        # Iteration ID selection
        selected_iteration = st.sidebar.selectbox(
            "Iteration ID",
            options=iteration_ids,
            index=0,
            format_func=lambda x: f"{x:03d}",
        )

        # Construct the sample ID from selected template and iteration
        sample_id = f"{selected_template:05d}:{selected_iteration:03d}"

        # Add proposal tier selection - only show if not using ranking mode
        proposal_tier = "CORRECT"  # Default value
        if prompt_type not in ["ranking", "interactive"]:
            proposal_tier = st.sidebar.selectbox(
                "Proposal Tier",
                options=[
                    "CORRECT",
                    "INCORRECT_EASY",
                    "INCORRECT_MEDIUM",
                    "INCORRECT_HARD",
                ],
                index=0,  # Default to CORRECT
            )

        few_shot_count = 0
        if prompt_type not in ["confidence", "interactive"]:
            few_shot_count = st.sidebar.slider(
                "Few-shot Examples",
                min_value=0,
                max_value=4,
                value=1,
            )

        # Only show few_shot_frames slider when not in sanity_check, ranking, confidence, or interactive mode
        few_shot_frames = 1  # Default value
        if prompt_type not in ["sanity_check", "ranking", "confidence", "interactive"]:
            few_shot_frames = st.sidebar.slider(
                "Few-shot Frames per Example",
                min_value=1,
                max_value=5,
                value=1,
            )

        # Move "Show raw messages" checkbox to the sidebar
        show_raw_messages = st.sidebar.checkbox("Show raw messages", value=False)

        # VLM configuration section
        st.sidebar.subheader("Vision Language Model")

        # Check if OpenRouter API key is configured
        if vlm_client.is_configured():
            # Provider selection
            selected_provider = st.sidebar.selectbox(
                "Select Provider",
                options=vlm_client.get_providers(),
                index=1,
            )

            # Model selection based on provider
            available_models = vlm_client.get_models_by_provider(selected_provider)
            # Use a safer default index that works for all providers
            default_index = (
                min(len(available_models) - 1, 0) if available_models else None
            )
            selected_model = st.sidebar.selectbox(
                "Select Model",
                options=available_models,
                index=default_index,
            )
        else:
            st.sidebar.warning(
                "OpenRouter API key not found. Set the OPENROUTER_API_KEY environment variable to enable VLM integration."
            )
            selected_model = None

        # Get sample from database based on prompt type
        with st.spinner(f"Fetching sample {sample_id} from database..."):
            if prompt_type == "ranking":
                sample = dataset_manager.get_ranking_sample(
                    sample_id,
                    1,  # Always use 1 frame for ranking prompts
                    few_shot_count=few_shot_count,
                )
                st.success(f"Successfully loaded ranking sample {sample_id}")
            elif prompt_type == "sanity_check":
                sample = dataset_manager.get_sanity_check_sample(  # type: ignore
                    sample_id,
                    proposal_tier,
                    few_shot_count=few_shot_count,
                )
                st.success(
                    f"Successfully loaded sanity check sample {sample_id} with tier {proposal_tier}"
                )
            elif prompt_type == "confidence":
                # Use binary sample retrieval but force few_shot_count to 0
                sample = dataset_manager.get_binary_sample(  # type: ignore
                    sample_id,
                    1,
                    proposal_tier,
                    few_shot_count=0,  # Force no few-shot examples for confidence
                    few_shot_frames=1,
                )
                st.success(
                    f"Successfully loaded confidence sample {sample_id} with tier {proposal_tier}"
                )
            elif prompt_type == "interactive":
                sample = dataset_manager.get_interactive_sample(sample_id)  # type: ignore
                st.success(f"Successfully loaded interactive sample {sample_id}")
            else:  # binary
                sample = dataset_manager.get_binary_sample(  # type: ignore
                    sample_id,
                    1,
                    proposal_tier,
                    few_shot_count=few_shot_count,
                    few_shot_frames=few_shot_frames,
                )
                st.success(
                    f"Successfully loaded binary sample {sample_id} with tier {proposal_tier}"
                )

        # For ranking samples, display the arrangement of proposals and their ordering
        if prompt_type == "ranking":
            with st.expander("Ranking Sample Details", expanded=True):
                display_ranking_info(st, sample)

        # Debug info about few-shot examples
        if few_shot_count > 0 and sample.few_shot:
            with st.expander(
                f"Few-shot examples ({len(sample.few_shot)}/{few_shot_count} retrieved)"
            ):
                for i, fs in enumerate(sample.few_shot):
                    st.subheader(f"Example {i+1}")
                    st.write(f"Puzzle ID: {fs.puzzle.id}")
                    st.write(f"Tier: {fs.proposal.tier}")
                    if fs.images:
                        # Debug output to verify images
                        st.write(f"Number of images: {len(fs.images)}")

                        # Create a container for better layout
                        img_container = st.container()
                        try:
                            # Create columns to display images adjacent to each other
                            with img_container:
                                num_images = len(fs.images)
                                if num_images > 0:
                                    img_cols = st.columns(num_images)
                                    for img_idx, img_path in enumerate(fs.images):
                                        # Force image load with error handling
                                        with img_cols[img_idx]:
                                            st.write(f"Frame {img_idx+1}:")
                                            # Check if image path exists and is properly formatted
                                            if img_path:
                                                display_image(
                                                    img_cols[img_idx], img_path
                                                )
                                            else:
                                                st.error("Invalid image path")
                        except Exception as e:
                            st.error(f"Error displaying image: {str(e)}")
                            logger.error(f"Image display error: {e}")
                    else:
                        st.warning("No images available for this example")

        # Initialize prompt manager with selected type
        prompt_manager = PromptManager(prompt_type=prompt_type)

        # Generate messages
        messages = prompt_manager.build_openai_messages(
            sample,
            insert_few_shot=(few_shot_count > 0),
        )

        # Track messages for debugging
        debug_track("messages", messages)
        debug_track("sample", sample)

        # Display messages
        st.subheader("Generated Messages")
        if prompt_type == "ranking":
            st.caption("Showing ranking proposals")
        else:
            st.caption(f"Showing prompt for {proposal_tier} proposal")

        # Display conversation history
        display_conversation_history(messages, [], show_raw_messages)

        # VLM integration - Send to model button and response display
        if vlm_client.is_configured() and selected_model:
            st.subheader("Send to Vision Language Model")

            # Create session state for tracking interactive mode state
            if "interactive_attempt" not in st.session_state:
                st.session_state.interactive_attempt = 1

            if "interactive_messages" not in st.session_state:
                st.session_state.interactive_messages = []

            if "interactive_status" not in st.session_state:
                st.session_state.interactive_status = None

            if "interactive_completed" not in st.session_state:
                st.session_state.interactive_completed = False

            if "continue_interaction" not in st.session_state:
                st.session_state.continue_interaction = False

            # Track interactive state for debugging
            if debug_mode:
                debug_track("interactive_attempt", st.session_state.interactive_attempt)
                debug_track(
                    "interactive_messages", st.session_state.interactive_messages
                )
                debug_track("interactive_status", st.session_state.interactive_status)

            # If we have previous interactive messages, display them
            if prompt_type == "interactive" and st.session_state.interactive_messages:
                st.subheader("Conversation History")
                display_conversation_history(
                    messages, st.session_state.interactive_messages, show_raw_messages
                )

            # Display attempts counter for interactive mode
            if prompt_type == "interactive":
                # Show reset button if we've already started
                if st.session_state.interactive_attempt > 1:
                    if st.session_state.interactive_completed:
                        st.markdown("---")
                        if st.button(
                            "Reset Interactive Session",
                            type="primary",
                            use_container_width=True,
                        ):
                            st.session_state.interactive_attempt = 1
                            st.session_state.interactive_messages = []
                            st.session_state.interactive_status = None
                            st.session_state.interactive_completed = False
                            st.session_state.continue_interaction = False
                            st.rerun()
                        st.markdown("---")
                    else:
                        if st.button("Reset Interactive Session"):
                            st.session_state.interactive_attempt = 1
                            st.session_state.interactive_messages = []
                            st.session_state.interactive_status = None
                            st.session_state.interactive_completed = False
                            st.session_state.continue_interaction = False
                            st.rerun()

            send_col, spinner_col = st.columns([1, 3])
            with send_col:
                send_button = st.button(
                    f"Send to {selected_model}",
                    use_container_width=True,
                    disabled=st.session_state.interactive_completed,
                )

            # Check if we should continue the interaction from the previous step
            if prompt_type == "interactive" and st.session_state.get(
                "continue_interaction", False
            ):
                # Reset the flag
                st.session_state.continue_interaction = False
                send_button = True

            if send_button:
                try:
                    # For interactive mode that's already in progress, we need to add the previous feedback
                    if (
                        prompt_type == "interactive"
                        and st.session_state.interactive_attempt > 1
                    ):
                        # Create a copy of the original messages
                        updated_messages = messages.copy()

                        # Add all the previous interactions from session state
                        for prev_msg in st.session_state.interactive_messages:
                            updated_messages.append(prev_msg)

                        # Use the updated messages instead of the original ones
                        messages_to_send = updated_messages
                    else:
                        messages_to_send = messages

                    with spinner_col:
                        with st.spinner(f"Sending to {selected_model}..."):
                            response = vlm_client.send_message(
                                messages_to_send, selected_model
                            )

                    # Display model response
                    with st.chat_message("assistant"):
                        st.write(response)
                        if show_raw_messages:
                            with st.expander(f"Raw message: assistant", expanded=True):
                                display_raw_message(
                                    st, {"role": "assistant", "content": response}
                                )

                    # Handle interactive evaluation if in interactive mode
                    if (
                        prompt_type == "interactive"
                        and not st.session_state.interactive_completed
                    ):
                        # Store the model response in session state
                        assistant_msg = {"role": "assistant", "content": response}
                        st.session_state.interactive_messages.append(assistant_msg)

                        # Process the response only if we haven't reached max attempts
                        if st.session_state.interactive_attempt <= 5:
                            # Evaluate the response without showing the title
                            status, screenshots, feedback = (
                                display_interactive_evaluation(
                                    response,
                                    sample.puzzle.model_dump(),
                                    st.session_state.interactive_attempt,
                                )
                            )

                            # Track evaluation results for debugging
                            debug_track("eval_status", status)
                            debug_track("eval_screenshots", screenshots)
                            debug_track("eval_feedback", feedback)

                            # Store the status
                            st.session_state.interactive_status = status

                            # If goal reached or max attempts reached, mark as completed
                            if (
                                status == "GOAL_REACHED"
                                or st.session_state.interactive_attempt >= 5
                            ):
                                st.session_state.interactive_completed = True
                            else:
                                # Create user message with feedback
                                user_content: List[Any] = []

                                # For GOAL_NOT_REACHED, we need to handle the [IMAGES] placeholder
                                if status == "GOAL_NOT_REACHED" and screenshots:
                                    # Split the feedback message at the [IMAGES] placeholder
                                    parts = feedback.split("[IMAGES]")

                                    if len(parts) == 2:
                                        # Remove any <CURRENT_CURSOR_POSITION> marker from the feedback
                                        first_part = (
                                            parts[0]
                                            .replace("<CURRENT_CURSOR_POSITION>", "")
                                            .strip()
                                        )
                                        second_part = (
                                            parts[1]
                                            .replace("<CURRENT_CURSOR_POSITION>", "")
                                            .strip()
                                        )

                                        # Add the first part of the text
                                        user_content.append(
                                            {"type": "text", "text": first_part}
                                        )

                                        # Add the screenshots
                                        for screenshot in screenshots[:5]:
                                            try:
                                                if isinstance(
                                                    screenshot, str
                                                ) and os.path.isfile(screenshot):
                                                    with open(screenshot, "rb") as f:
                                                        img_data = f.read()
                                                        encoded_img = base64.b64encode(
                                                            img_data
                                                        ).decode("utf-8")
                                                        user_content.append(
                                                            {
                                                                "type": "image_url",
                                                                "image_url": {
                                                                    "url": f"data:image/png;base64,{encoded_img}",
                                                                    "detail": "high",
                                                                },
                                                            }
                                                        )
                                            except Exception as e:
                                                logger.error(
                                                    f"Failed to process screenshot: {e}"
                                                )

                                        # Add the second part of the text
                                        user_content.append(
                                            {"type": "text", "text": second_part}
                                        )
                                    else:
                                        # Fallback if [IMAGES] placeholder not found
                                        user_content.append(
                                            {"type": "text", "text": feedback}
                                        )
                                else:
                                    # For other statuses, just write the feedback
                                    print(f"DEBUG - UI Raw feedback: {feedback}")
                                    st.write(feedback)

                                # Create the user message with feedback
                                user_msg = {"role": "user", "content": user_content}

                                # Add to interactive messages
                                st.session_state.interactive_messages.append(user_msg)

                                # Display the feedback to the user with images in the right place
                                with st.chat_message("user"):
                                    if status == "GOAL_NOT_REACHED" and screenshots:
                                        # Split the feedback message at the [IMAGES] placeholder
                                        parts = feedback.split("[IMAGES]")

                                        if len(parts) == 2:
                                            # Remove any <CURRENT_CURSOR_POSITION> marker from the feedback
                                            first_part = (
                                                parts[0]
                                                .replace(
                                                    "<CURRENT_CURSOR_POSITION>", ""
                                                )
                                                .strip()
                                            )
                                            second_part = (
                                                parts[1]
                                                .replace(
                                                    "<CURRENT_CURSOR_POSITION>", ""
                                                )
                                                .strip()
                                            )

                                            # Write the first part
                                            st.write(first_part)

                                            # Display screenshots in columns
                                            if len(screenshots) > 1:
                                                # Limit to max 5 columns for better display
                                                cols = st.columns(
                                                    min(len(screenshots), 5)
                                                )
                                                for col_idx, screenshot in enumerate(
                                                    screenshots[:5]
                                                ):
                                                    try:
                                                        if isinstance(
                                                            screenshot, str
                                                        ) and os.path.isfile(
                                                            screenshot
                                                        ):
                                                            display_image(
                                                                cols[col_idx],
                                                                screenshot,
                                                            )
                                                    except Exception as e:
                                                        logger.error(
                                                            f"Failed to display screenshot: {e}"
                                                        )
                                            else:
                                                # Single image
                                                img_container = st.container()
                                                try:
                                                    if isinstance(
                                                        screenshots[0], str
                                                    ) and os.path.isfile(
                                                        screenshots[0]
                                                    ):
                                                        display_image(
                                                            img_container,
                                                            screenshots[0],
                                                        )
                                                except Exception as e:
                                                    logger.error(
                                                        f"Failed to display screenshot: {e}"
                                                    )

                                            # Write the second part
                                            st.write(second_part)

                                    else:
                                        # For other statuses, just write the feedback
                                        st.write(feedback)

                                    if show_raw_messages:
                                        with st.expander(
                                            f"Raw message: user", expanded=True
                                        ):
                                            display_raw_message(st, user_msg)

                                # Increment the attempt counter
                                st.session_state.interactive_attempt += 1

                                # Provide button to continue the interaction
                                if st.button(
                                    "Continue to next attempt",
                                    key=f"continue_{st.session_state.interactive_attempt}",
                                ):
                                    # Instead of just rerunning, we need to trigger the send to model
                                    # We'll set a session state flag to indicate we should send the message
                                    st.session_state.continue_interaction = True
                                    st.rerun()

                except Exception as e:
                    st.error(f"Error sending messages to {selected_model}: {str(e)}")
                    logger.error(f"VLM API error: {str(e)}")

    except Exception as e:
        logger.error(f"Error loading sample from database: {str(e)}")
        st.error(f"Error loading sample from database: {str(e)}")
        st.info("Please check your database connection and sample ID.")
        st.exception(e)

        # Track exception for debugging
        if debug_mode:
            debug_track("exception", str(e))
            debug_track("exception_type", type(e).__name__)

    # Additional information
    st.sidebar.subheader("About")
    st.sidebar.info(
        """
        This tool helps visualize how different prompt types will appear 
        when sent to an LLM for physics simulation analysis.
        Select different prompt types and options to see how they affect 
        the generated messages.
        You can also send the prompt to various Vision Language Models using
        the OpenRouter integration.
        """
    )

    # Display debug information if debug mode is enabled
    if debug_mode:
        with debug_container:
            st.header("Debug Information")

            # Add tabs for different debug views
            debug_tabs = st.tabs(["Variables", "Session State", "Current Frame"])

            # Variables tab - show tracked variables
            with debug_tabs[0]:
                st.subheader("Tracked Variables")
                if st.session_state.debug_vars:
                    for var_name, var_value in st.session_state.debug_vars.items():
                        with st.expander(f"{var_name}"):
                            # Use pretty printing for better formatting
                            st.code(pprint.pformat(var_value, depth=3, compact=False))
                else:
                    st.info("No variables have been tracked yet.")

            # Session State tab - show all session state
            with debug_tabs[1]:
                st.subheader("Session State")
                # Filter out debug_vars to avoid recursion
                filtered_state = {
                    k: v for k, v in st.session_state.items() if k != "debug_vars"
                }
                st.json(filtered_state)

            # Current Frame tab - show current frame info
            with debug_tabs[2]:
                st.subheader("Current Frame")
                frame = inspect.currentframe()
                if frame:
                    # Get local variables from the current frame
                    local_vars = {
                        k: str(v)
                        for k, v in frame.f_locals.items()
                        if not k.startswith("_")
                        and k != "debug_vars"
                        and not inspect.ismodule(v)
                        and not inspect.isfunction(v)
                    }
                    st.json(local_vars)


if __name__ == "__main__":
    main()
