import json
import base64
from enum import Enum
import tempfile
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import Dict, Any
from vertexai.generative_models import Part

from ..vertex_ai.base_vertex_ai import BaseVertexAI


class SupportType(Enum):
    NOTHING = "nothing"
    SUPPORT = "support"
    ADVICE = "advice"
    ALERT = "alert"

    @classmethod
    def to_comma_string(cls):
        return ",".join(member.name for member in cls)


class SupportInfo(BaseModel):
    support_type: str = Field(
        description=f"type of support: {SupportType.to_comma_string()}",
    )
    message: str = Field(description="message to the user about the support_type")

    @validator("support_type")
    def validate_support_type(cls, v):
        """サポートタイプが有効な値であることを検証"""
        valid_types = [item.value for item in SupportType]
        if v not in valid_types:
            raise ValueError(f'support_type must be one of: {", ".join(valid_types)}')
        return v

    @classmethod
    def from_json_data(cls, json_data: Dict[str, Any]) -> "SupportInfo":
        return cls(support_type=json_data["support_type"], message=json_data["message"])

    def make_message(self):
        return f"{self.support_type}: {self.message}"


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

    def process_image(
        self, filename
    ):  # Not strictly needed by TaskSupporter if using Part.from_data
        file_path = self.temp_path / filename
        with open(file_path, "rb") as f:
            return f.read()

    def cleanup(self):
        self._temp_dir.cleanup()

    def __del__(self):
        if hasattr(self, "_temp_dir"):
            self._temp_dir.cleanup()


class TaskSupporter(BaseVertexAI):
    def __init__(self):
        super().__init__()
        self.image_processor = ImageProcessor()
        self.system_prompt = """
You are an assistant designed to provide **minimal yet effective support** based on Screen Image of a user's activity on their PC.

Your job is to analyze the work log and respond only when **clearly beneficial** to the user. Assume the user is generally capable and prefers to work independently unless there's strong evidence to intervene.

You will receive past support logs, so please avoid offering support that duplicates previous content.
---

### Objective

* Improve the user's productivity and ensure safe operation.
* Offer precise support only when necessary, avoiding over-assistance.

---

## Types of Support

### 1. **Advise**

**Purpose**: Offer suggestions to improve the user's workflow efficiency.
**Trigger Conditions**:

* The user is performing tasks inefficiently or manually when shortcuts/tools exist.
* There's an obviously faster or more elegant method available.
* The user's workflow shows room for objective improvement.

**Examples**:

* “You can perform this operation more quickly using `Ctrl + D`.”
* “If you’re using multiple terminals, you might find `tmux` helpful.”

---

### 2. **Support**

**Purpose**: Help the user when they're facing issues or appear to be stuck.
**Trigger Conditions**:

* Errors or bugs are halting progress.
* The user is researching something inefficiently or using outdated sources.
* There's evidence of uncertainty or confusion in the log.

**Examples**:

* “This error might be due to a Python package conflict. Try checking with `pip freeze`.”
* “For this topic, you may want to limit your search to sources after 2024 for better results.”

---

### 3. **Alert**

**Purpose**: Warn the user about operations that are dangerous or high-risk.
**Trigger Conditions**:

* The user is about to perform irreversible actions (e.g., deleting critical files).
* There's a security concern (e.g., leaking API keys).
* The user is making a risky decision based on a misunderstanding.

**Examples**:

* “This script uses a public API key from GitHub. Please be careful not to leak sensitive data.”

---

## Output Format
You must output in the following
  - In Japanese
  - message is short and concise
        """
        self.response_scheme = {
            "type": "OBJECT",
            "properties": {
                "support_type": {
                    "type": "STRING",
                    "description": "type of support: NOTHING,SUPPORT,ADVICE,ALERT",
                },
                "message": {
                    "type": "STRING",
                    "description": "message to the user about the support_type",
                },
            },
            "required": ["support_type", "message"],
        }

    def _make_contents(self, encoded_frames: list[str]) -> list:
        image_parts = []
        if encoded_frames:
            self.logger.info(
                f"Processing {len(encoded_frames)} image(s) for TaskSupporter."
            )
            for i, frame_b64 in enumerate(encoded_frames):
                try:
                    image_data = base64.b64decode(frame_b64)
                    image_parts.append(
                        Part.from_data(data=image_data, mime_type="image/png")
                    )
                except Exception as e:
                    self.logger.error(
                        f"Error decoding or creating Part for frame {i}: {e}"
                    )
        else:
            self.logger.info("No frames provided to TaskSupporter.")

        contents = [self.system_prompt] + image_parts
        return contents

    def get_support(self, encoded_frames: list[str]) -> SupportInfo:
        contents = self._make_contents(encoded_frames)

        response = self.invoke(contents)
        support_info = SupportInfo.from_json_data(json.loads(response.text))
        return support_info

    def cleanup(self):
        if hasattr(self, "image_processor") and self.image_processor:
            self.image_processor.cleanup()
