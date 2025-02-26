import base64
import os
from typing import cast

import litellm
from litellm.types.utils import ModelResponse

# Set your API key (replace with your actual key)
os.environ["OPENAI_API_KEY"] = (
    "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"
)

# Read and encode the local image file in base64
with open("a.png", "rb") as f:
    img_data = f.read()
    encoded_img = base64.b64encode(img_data).decode("utf-8")

# Construct the message payload with text and the encoded image.
# (If your model requires image URLs instead, you'll need to host the image online.)
message = {
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": "What does this image represent? Please answer concisely.",
        },
        {
            "type": "image_url",
            "image_url": {
                "url": "data:image/png;base64," + encoded_img,
            },
        },
    ],
}

# Call the model using LiteLLM; adjust the model name if needed (e.g., use "gpt-4-vision-preview" if required)
response = cast(
    ModelResponse, litellm.completion(model="openai/gpt-4o", messages=[message])
)

print("Response:", cast(litellm.Choices, response.choices[0]).message.content)
