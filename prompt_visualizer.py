from typing import Any

import streamlit as st
from loguru import logger

from src.managers import DatasetManager, MongoDBManager, PromptManager
from src.utils.db_schemas import RankingSampleData
from src.utils.vlm_client import VLMClient


def display_image(container, image_url: str) -> None:
    """Helper function to display images with consistent sizing"""
    width = 200  # Fixed width of 200px
    if image_url.startswith("data:image/png;base64,"):
        # For base64 encoded images
        container.markdown(
            f'<img src="{image_url}" style="width:{width}px;">',
            unsafe_allow_html=True,
        )
    else:
        # For file path images
        try:
            container.image(image_url, width=width)
        except Exception as e:
            logger.error(f"Failed to display image from path {image_url}: {e}")
            container.error(f"Failed to load image: {str(e)}")


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
                        img_container = st.container()
                        display_image(img_container, image_url)

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
                # Create a copy of the image_url dict to avoid modifying the original
                image_url_copy = item_copy["image_url"].copy()
                # Replace base64 data with placeholder
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


def main() -> None:
    st.set_page_config(
        page_title="PhysIQ Prompt Visualizer",
        page_icon="🧠",
        layout="wide",
    )

    st.title("PhysIQ Prompt Visualizer")
    st.write("Visualize the prompts generated for the PhysIQ physics simulation task.")

    # Initialize VLM client
    vlm_client = VLMClient()

    # Sidebar configuration
    st.sidebar.title("Configuration")

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
            options=["sanity_check", "binary", "ranking"],  # Added "ranking"
            index=0,
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
        if prompt_type != "ranking":
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

        few_shot_count = st.sidebar.slider(
            "Few-shot Examples",
            min_value=0,
            max_value=4,
            value=1,
        )

        # Only show few_shot_frames slider when not in sanity_check or ranking mode
        few_shot_frames = 1  # Default value
        if prompt_type not in ["sanity_check", "ranking"]:
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
                index=0,
            )

            # Model selection based on provider
            available_models = vlm_client.get_models_by_provider(selected_provider)
            selected_model = st.sidebar.selectbox(
                "Select Model",
                options=available_models,
                index=0 if available_models else None,
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
                    few_shot_frames=1,  # Always use 1 frame for ranking few-shot examples
                )
                st.success(f"Successfully loaded ranking sample {sample_id}")
            elif prompt_type == "sanity_check":
                sample = dataset_manager.get_sanity_check_sample(
                    sample_id,
                    proposal_tier,
                    few_shot_count=few_shot_count,
                )
                st.success(
                    f"Successfully loaded sanity check sample {sample_id} with tier {proposal_tier}"
                )
            else:  # binary
                sample = dataset_manager.get_binary_sample(
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

        # Display messages
        st.subheader("Generated Messages")
        if prompt_type == "ranking":
            st.caption("Showing ranking proposals")
        else:
            st.caption(f"Showing prompt for {proposal_tier} proposal")

        # Improved few-shot rendering logic
        if few_shot_count > 0 and sample.few_shot and len(sample.few_shot) > 0:
            # Always display the system message first
            render_message(messages[0])

            # Display raw message if enabled
            if show_raw_messages:
                with st.expander(
                    f"Raw message: {messages[0].get('role')}", expanded=True
                ):
                    display_raw_message(st, messages[0])

            # Then the initial user message explaining the task
            if len(messages) > 1:
                render_message(messages[1])
                if show_raw_messages:
                    with st.expander(
                        f"Raw message: {messages[1].get('role')}", expanded=True
                    ):
                        display_raw_message(st, messages[1])

            # Check if we have few-shot examples
            if (
                len(messages) > 3
            ):  # At minimum: system + user + few-shot user + few-shot assistant
                i = 2  # Start after system and initial user message

                # Process messages in pairs until we reach the final user message
                while i < len(messages) - 1:
                    # Check if this looks like a few-shot pair (user followed by assistant)
                    if (
                        messages[i].get("role") == "user"
                        and i + 1 < len(messages)
                        and messages[i + 1].get("role") == "assistant"
                    ):
                        # Display user message (question with image)
                        render_message(messages[i])
                        if show_raw_messages:
                            with st.expander(
                                f"Raw message: {messages[i].get('role')}", expanded=True
                            ):
                                display_raw_message(st, messages[i])

                        # Display assistant message (answer)
                        render_message(messages[i + 1])
                        if show_raw_messages:
                            with st.expander(
                                f"Raw message: {messages[i+1]}.get('role')",
                                expanded=True,
                            ):
                                display_raw_message(st, messages[i + 1])

                        i += 2  # Move to the next potential pair
                    else:
                        # If not a few-shot pair, we've likely reached the final user question
                        break

                # Display the final user question (current problem)
                while i < len(messages):
                    render_message(messages[i])
                    if show_raw_messages:
                        with st.expander(
                            f"Raw message: {messages[i].get('role')}", expanded=True
                        ):
                            display_raw_message(st, messages[i])
                    i += 1
            else:
                # No few-shot examples in the messages
                for i in range(2, len(messages)):
                    render_message(messages[i])
                    if show_raw_messages:
                        with st.expander(
                            f"Raw message: {messages[i].get('role')}", expanded=True
                        ):
                            display_raw_message(st, messages[i])
        else:
            # No few-shot examples requested, just show all messages sequentially
            for i, msg in enumerate(messages):
                render_message(msg)
                if show_raw_messages:
                    with st.expander(f"Raw message: {msg.get('role')}", expanded=True):
                        display_raw_message(st, msg)

        # VLM integration - Send to model button and response display
        if vlm_client.is_configured() and selected_model:
            st.subheader("Send to Vision Language Model")

            send_col, spinner_col = st.columns([1, 3])
            with send_col:
                send_button = st.button(
                    f"Send to {selected_model}", use_container_width=True
                )

            if send_button:
                try:
                    with spinner_col:
                        with st.spinner(f"Sending to {selected_model}..."):
                            response = vlm_client.send_message(messages, selected_model)

                    # Display model response
                    st.subheader("Model Response")
                    st.markdown("---")
                    with st.chat_message("assistant"):
                        st.write(response)
                    st.markdown("---")

                    # For ranking prompts, provide a simple way to interpret the response
                    if prompt_type == "ranking" and response:
                        with st.expander("Response Analysis", expanded=True):
                            st.write("Analyzing model response for ranking...")

                            # Try to extract ranking from response
                            try:
                                # Look for patterns like [1,2,3,4] or 1,2,3,4
                                import re

                                # Look for sequences of digits possibly separated by commas or spaces
                                rank_pattern = re.search(
                                    r"(?:\[|\s|^)(\d+\s*[, ]\s*\d+\s*[, ]\s*\d+\s*[, ]\s*\d+)(?:\]|\s|$)",
                                    response,
                                )

                                if rank_pattern:
                                    ranking_str = rank_pattern.group(1)
                                    # Clean up and convert to list of integers
                                    ranking = [
                                        int(x.strip())
                                        for x in re.split(r"[,\s]+", ranking_str)
                                        if x.strip()
                                    ]

                                    # Display extracted ranking
                                    st.write(f"Extracted ranking: {ranking}")

                                    assert isinstance(sample, RankingSampleData)
                                    correct_ranking = sample.metadata.correct_ranking
                                    st.write(
                                        f"Expected ranking: {[i+1 for i in range(len(correct_ranking))]}"
                                    )

                                    # Calculate simple accuracy (how many positions are correct)
                                    if len(ranking) == len(correct_ranking):
                                        correct_positions = sum(
                                            1
                                            for a, b in zip(
                                                ranking,
                                                [
                                                    i + 1
                                                    for i in range(len(correct_ranking))
                                                ],
                                            )
                                            if a == b
                                        )
                                        accuracy = correct_positions / len(ranking)
                                        st.write(
                                            f"Ranking accuracy: {accuracy:.2f} ({correct_positions}/{len(ranking)} correct positions)"
                                        )
                                else:
                                    st.warning(
                                        "Couldn't extract clear ranking from the response"
                                    )
                            except Exception as e:
                                st.error(f"Error analyzing response: {str(e)}")

                except Exception as e:
                    st.error(f"Error sending messages to {selected_model}: {str(e)}")
                    logger.error(f"VLM API error: {str(e)}")

    except Exception as e:
        logger.error(f"Error loading sample from database: {str(e)}")
        st.error(f"Error loading sample from database: {str(e)}")
        st.info("Please check your database connection and sample ID.")
        st.exception(e)

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


if __name__ == "__main__":
    main()
