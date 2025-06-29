import json
from datetime import datetime
from pydantic import BaseModel, Field
from vertexai.generative_models import Image, Part

import base64
import tempfile
from pathlib import Path
from agents.vertex_ai.base_vertex_ai import BaseVertexAI


class ScreenInfo(BaseModel):
    description: str = Field(
        description="high detail description of what user is doing",
    )
    timestamp: str


class ImageProcessor:
    def __init__(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self._temp_dir.name)

    def save_image(self, base64_data, filename):
        image_data = base64.b64decode(base64_data)
        file_path = self.temp_path / filename
        with open(file_path, "wb") as f:
            f.write(image_data)
        return file_path

    def process_image(self, filename):
        file_path = self.temp_path / filename
        with open(file_path, "rb") as f:
            return f.read()

    def cleanup(self):
        self._temp_dir.cleanup()

    def __del__(self):
        if hasattr(self, "_temp_dir"):
            self._temp_dir.cleanup()


class ScreenAnalyzer(BaseVertexAI):
    def __init__(self):
        super().__init__()
        self.system_prompt = """
            You are given a screenshot of the user's screen.
            You should analyze the screenshot and extract detail
            information about what the user is doing.

            points to consider:
            - what is the user doing?
            - what is the user's task?
            - what is the user focusing on?
            - what is the user using?
            - what is the user looking at?
            - what title is the user looking at on the web?
            ## User request
            {query}
            """
        self.response_scheme = {
            "type": "OBJECT",
            "properties": {
                "description": {
                    "type": "STRING",
                    "description": "high detail description of what user is doing",
                }
            },
            "required": ["description"],
        }

        self.image_processor = ImageProcessor()

    def _make_contents(self, encoded_frames: list[str], user_query: str):
        image_parts = []
        self.logger.info(
            f"Begin processing {len(encoded_frames)} images "
            f"for query '{user_query}'"
        )
        for i, encoded_frame in enumerate(encoded_frames):
            image_data = base64.b64decode(encoded_frame)
            image_part = Part.from_data(data=image_data, mime_type="image/png")
            image_parts.append(image_part)

        current_system_prompt = self.system_prompt.format(
            query=user_query if user_query else "Describe the screen."
        )

        contents = [current_system_prompt] + image_parts
        return contents

    def analysis(self, encoded_frames: list[str], user_query: str = "") -> ScreenInfo:
        self.logger.info(
            f"Starting analysis for query '{user_query}' "
            f"with {len(encoded_frames)} image(s)"
        )
        contents = self._make_contents(encoded_frames, user_query)
        response = self.invoke(contents)

        parsed_response = json.loads(response.text)
        description = parsed_response.get("description", "")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        screen_info = ScreenInfo(description=description, timestamp=timestamp)

        return screen_info

    def cleanup(self):
        self.image_processor.cleanup()
