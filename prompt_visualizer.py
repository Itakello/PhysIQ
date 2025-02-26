import json
from typing import Any

import streamlit as st
from loguru import logger

from src.managers import DatasetManager, MongoDBManager, PromptManager
from src.utils.const import PROMPT_COT, PROMPT_DETAILED, PROMPT_DIRECT


def render_message(message: dict[str, Any]) -> None:
    """Render a single message in the Streamlit chat interface"""
    role = message.get("role", "system")
    content = message.get("content", "")

    with st.chat_message(role):
        # Handle different content types
        if isinstance(content, str):
            st.write(content)
        elif isinstance(content, list):
            for item in content:
                if item["type"] == "text":
                    st.write(item["text"])
                elif item["type"] == "image_url":
                    image_url = item["image_url"]["url"]
                    if image_url.startswith("data:image/png;base64,"):
                        # This is a base64 encoded image
                        st.markdown(
                            f'<img src="{image_url}" style="max-width:25%">',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.image(image_url, use_column_width=True)


def display_raw_message(message: dict[str, Any]) -> None:
    """Display the raw message structure for debugging"""
    with st.expander("Raw message data"):
        # Replace large base64 strings with placeholders for readability
        display_msg = json.loads(json.dumps(message))
        if isinstance(display_msg.get("content"), list):
            for item in display_msg.get("content", []):
                if item.get("type") == "image_url" and "image_url" in item:
                    item["image_url"]["url"] = "data:image/png;base64,[BASE64_DATA]"
        st.json(display_msg)


def main() -> None:
    st.set_page_config(
        page_title="PhysIQ Prompt Visualizer",
        page_icon="🧠",
        layout="wide",
    )

    st.title("PhysIQ Prompt Visualizer")
    st.write("Visualize the prompts generated for the PhysIQ physics simulation task.")

    # Sidebar configuration
    st.sidebar.title("Configuration")

    prompt_type = st.sidebar.selectbox(
        "Prompt Type",
        [PROMPT_DIRECT, PROMPT_DETAILED, PROMPT_COT],
        format_func=lambda x: {
            PROMPT_DIRECT: "Direct (Yes/No)",
            PROMPT_DETAILED: "Detailed (Yes/No with Physics Parameters)",
            PROMPT_COT: "Chain-of-Thought (Step-by-step Reasoning)",
        }.get(x, x),
    )

    # Database sample configuration
    sample_id = st.sidebar.text_input("Sample ID", value="00000:000")

    few_shot_count = st.sidebar.slider(
        "Few-shot Examples",
        min_value=0,
        max_value=4,
        value=0,
    )

    # Initialize database managers
    try:
        # Initialize managers
        mongo_manager = MongoDBManager(db_name="physiq_db")
        dataset_manager = DatasetManager(db_manager=mongo_manager)

        # Get sample from database
        with st.spinner("Fetching sample from database..."):
            sample = dataset_manager.get_sample(
                sample_id,
                1,  # Only one interaction
                "CORRECT",
                few_shot_count=few_shot_count,
            )

        st.success(f"Successfully loaded sample {sample_id}")

        # Debug info about few-shot examples
        if few_shot_count > 0:
            assert sample.few_shot, "Few-shot examples should not be empty"
            with st.expander(
                f"Few-shot examples ({len(sample.few_shot)}/{few_shot_count} retrieved)"
            ):
                for i, fs in enumerate(sample.few_shot):
                    st.subheader(f"Example {i+1}")
                    st.write(f"Puzzle ID: {fs.puzzle.id}")
                    st.write(f"Is successful: {fs.proposal.tier == 'CORRECT'}")
                    if fs.images:
                        st.write(f"Images: {', '.join(fs.images)}")
                        # Display first image if available
                        try:
                            st.image(fs.images[0], width=200)
                        except Exception as e:
                            st.error(f"Error displaying image: {str(e)}")

        # Initialize prompt manager with selected type
        prompt_manager = PromptManager(prompt_type=prompt_type)

        # Generate messages
        messages = prompt_manager.build_openai_messages(
            sample,
            insert_few_shot=(few_shot_count > 0),
        )

        # Display messages
        st.subheader("Generated Messages")

        # Improved few-shot rendering logic
        if few_shot_count > 0 and len(sample.few_shot) > 0:
            # Always display the system message first
            render_message(messages[0])

            # Then the initial user message explaining the task
            if len(messages) > 1:
                render_message(messages[1])

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

                        # Display assistant message (answer)
                        render_message(messages[i + 1])

                        i += 2  # Move to the next potential pair
                    else:
                        # If not a few-shot pair, we've likely reached the final user question
                        break

                # Display the final user question (current problem)
                while i < len(messages):
                    render_message(messages[i])
                    i += 1
            else:
                # No few-shot examples in the messages
                for i in range(2, len(messages)):
                    render_message(messages[i])
        else:
            # No few-shot examples requested, just show all messages sequentially
            for msg in messages:
                render_message(msg)

        # Show raw messages for debugging
        if st.checkbox("Show raw messages"):
            for i, msg in enumerate(messages):
                with st.expander(f"Raw message {i+1} ({msg.get('role')})"):
                    display_raw_message(msg)

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
        """
    )


if __name__ == "__main__":
    main()
