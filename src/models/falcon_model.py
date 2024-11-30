from io import BytesIO
from typing import Optional

import requests
import torch
import transformers as tf
import weave
from itakello_logging import ItakelloLogging
from PIL import Image
from pydantic import Field, model_validator

from ..config import const
from .custom_model import CustomModel, ModelBackend

logger = ItakelloLogging(debug=False).get_logger(__name__)


class FalconModel(CustomModel):
    backend: ModelBackend = ModelBackend.HF
    model: Optional[tf.PreTrainedModel] = Field(default=None)
    processor: Optional[tf.LlavaNextProcessor] = Field(default=None)

    @model_validator(mode="after")
    def initialize_model(self) -> "FalconModel":
        assert self.name, logger.error("Model name must be provided")
        try:
            self.model = tf.LlavaNextForConditionalGeneration.from_pretrained(
                "tiiuae/falcon-11B-vlm", torch_dtype=torch.bfloat16
            )
        except Exception as e:
            logger.error(f"Error loading model {self.id}: {e}")
            exit(1)
        # Unpack the processor if it returns both the processor and some configuration dict
        processor_tuple = tf.LlavaNextProcessor.from_pretrained(
            "tiiuae/falcon-11B-vlm", tokenizer_class="PreTrainedTokenizerFast"
        )
        if isinstance(processor_tuple, tuple):
            self.processor, _ = processor_tuple
        else:
            self.processor = processor_tuple

        # Set deprecated attributes directly
        self.processor.patch_size = 16  # Example value, adjust as needed
        self.processor.vision_feature_select_strategy = (
            "mean"  # Example value, adjust as needed
        )

        # Set tokenizer padding side
        self.processor.tokenizer.padding_side = "left"

        return self

    @weave.op
    def predict(self, question: str, image_url: str) -> str:
        if self.model is None or self.processor is None:
            logger.error("Model or processor not initialized.")
            return ""

        # Load and preprocess image
        response = requests.get(image_url)
        if response.status_code != 200:
            logger.error(
                f"Error fetching image from URL {image_url}: {response.status_code}"
            )
            return ""

        try:
            image = Image.open(BytesIO(response.content))
        except Exception as e:
            logger.error(f"Error opening image from URL {image_url}: {e}")
            return ""

        # Process image input
        try:
            image_features = self.processor.image_processor(
                [image], return_tensors="pt"
            ).to(const.DEVICE)
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return ""

        # Prepare prompt and tokenize input
        prompt = f"User:<image>\n{question} Falcon:"
        tokenizer = tf.AutoTokenizer.from_pretrained("tiiuae/falcon-11B-vlm")
        prompt_ids = tokenizer(prompt, return_tensors="pt", padding=True).to(
            const.DEVICE
        )

        # Combine inputs for the model
        inputs = {
            "input_ids": prompt_ids.input_ids,
            "pixel_values": image_features.pixel_values,
        }

        # Generate response
        self.model.to(const.DEVICE)
        with torch.no_grad():
            output = self.model.generate(**inputs, max_new_tokens=256)

        # Decode and return
        generated_captions = tokenizer.decode(
            output[0], skip_special_tokens=True
        ).strip()
        return generated_captions


if __name__ == "__main__":
    model = FalconModel(
        name="falcon-11B-vlm",
        id="tiiuae/falcon-11B-vlm",
    )
    print(
        model.predict(
            "What's this?",
            "https://th.bing.com/th/id/OIP.fOuB9rLGFXQ5GRCTM6dC1QAAAA?w=252&h=190&c=7&r=0&o=5&dpr=1.1&pid=1.7",
        )
    )
