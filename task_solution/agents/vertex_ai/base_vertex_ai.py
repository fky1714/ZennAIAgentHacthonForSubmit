import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from google.genai import types, Client
from utils.logger import Logger


class BaseVertexAI:
    def __init__(self, model_name):
        project_id = os.getenv("GCP_PROJECT")
        location = os.getenv("GCP_LOCATION", "us-central1")
        vertexai.init(project=project_id, location=location)
        self.model_name = model_name
        self.response_scheme = None
        self.logger = Logger(name=self.__class__.__name__).get_logger()

    @property
    def model(self) -> GenerativeModel:
        return GenerativeModel(self.model_name)

    @property
    def generation_config(self):
        # Default config for JSON output
        if self.response_scheme:
            return GenerationConfig(
                response_mime_type="application/json",
                response_schema=self.response_scheme,
            )
        # Default config for text/plain output if no schema is provided
        return GenerationConfig(
            response_mime_type="text/plain",
        )

    def invoke(self, contents):
        # Truncate log output for contents if it's too long
        log_contents = str(contents)
        if len(log_contents) > 100: # Log approx first 100 chars
            log_contents = log_contents[:100] + "..."
        self.logger.info(f"contents > {log_contents}")
        response = self.model.generate_content(
            contents,
            generation_config=self.generation_config,
        )
        self.logger.info(f"response > {response}")
        return response
