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
        return GenerationConfig(
            response_mime_type="application/json",
            response_schema=self.response_scheme,
        )

    def invoke(self, contents):
        self.logger.info(f"contents > {contents[30:]}")
        response = self.model.generate_content(
            contents,
            generation_config=self.generation_config,
        )
        self.logger.info(f"response > {response}")
        return response
