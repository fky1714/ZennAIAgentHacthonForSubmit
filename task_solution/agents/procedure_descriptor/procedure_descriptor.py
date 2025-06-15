import json
from pydantic import BaseModel, Field
from typing import Dict, Any
from vertexai.generative_models import Part
from ..vertex_ai.base_vertex_ai import BaseVertexAI


class ProcedureStep(BaseModel):
    section: str = Field(
        description="section of the procedure",
    )
    description: str = Field(
        description="high detail description of what user is doing",
    )


class ProcedureOutput(BaseModel):
    title: str = Field(description="title of the procedure")
    steps: list[ProcedureStep] = Field(description="steps of the procedure")

    @classmethod
    def from_json_data(cls, json_data: Dict[str, Any]) -> "ProcedureOutput":
        steps = []
        for step_data in json_data["steps"]:
            step = ProcedureStep(
                section=step_data["section"], description=step_data["description"]
            )
            steps.append(step)

        return cls(title=json_data["title"], steps=steps)

    def to_document(self):
        md_content = f"# {self.title}\n\n"
        for step in self.steps:
            md_content += f"## {step.section}\n{step.description}\n\n"
        return md_content


class ProcedureDescriptor(BaseVertexAI):
    def __init__(self, model_name="gemini-2.0-flash"):
        super().__init__(model_name=model_name)

        self.system_prompt = """
            You are given a records of pc task.
            You should analyze the records and extract detail information about what the user is doing.

            # important points
            - Ignore any logs related to starting/stopping recording in the TaskSolution WebApp, as these are automatically included in logs but not relevant to the procedure
            - The procedure document should focus on the purpose indicated by the task_name, extracting only the steps necessary to execute that task from the logs
            - Ignore any logs that are not needed for the procedure
            - Generalize the procedure steps
            - However, be sure to include all information necessary for the procedure

            ## Formatting
            - In Japanese.

            ## Task name
            {task_name}

            ## User request
            {query}
        """

        self.response_scheme = {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING"},
                "steps": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "section": {
                                "type": "STRING",
                            },
                            "description": {
                                "type": "STRING",
                            },
                        },
                        "required": ["section", "description"],
                    },
                },
            },
            "required": ["title", "steps"],
        }

    def analyze_video(self, task_name, video_uri, user_query) -> ProcedureOutput:
        video_file = Part.from_uri(
            video_uri,
            mime_type="video/mp4",
        )
        self.system_prompt = self.system_prompt.format(
            task_name=task_name, query=user_query
        )
        contents = [video_file, self.system_prompt]
        response = self.model.generate_content(
            contents=contents,
            generation_config=self.generation_config,
        )

        output = ProcedureOutput.from_json_data(json.loads(response.text))
        return output
