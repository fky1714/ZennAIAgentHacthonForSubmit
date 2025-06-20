import json
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from vertexai.generative_models import Part
from ..vertex_ai.base_vertex_ai import BaseVertexAI


class DetailedStep(BaseModel):
    step_number: int = Field(description="Step number in the procedure")
    step_title: str = Field(descriotion="Simple step title")
    operation: str = Field(description="Specific operation to perform")


class ProcedureOutput(BaseModel):
    procedure_overview: str = Field(
        description="Brief description of what the procedure accomplishes"
    )
    prerequisites: Optional[str] = Field(
        description="Required state/preparations before starting the procedure",
        default=None,
    )
    detailed_steps: List[DetailedStep] = Field(
        description="Numbered specific operation steps"
    )
    completion_verification: str = Field(
        description="How to confirm the procedure completed successfully"
    )
    notes: Optional[str] = Field(
        description="Important points and troubleshooting", default=None
    )

    @classmethod
    def from_json_data(cls, json_data: Dict[str, Any]) -> "ProcedureOutput":
        detailed_steps = []
        for i, step_data in enumerate(json_data["detailed_steps"]):
            step = DetailedStep(
                step_number=i + 1,
                step_title=step_data["step_title"],
                operation=step_data["operation"],
            )
            detailed_steps.append(step)

        return cls(
            procedure_overview=json_data["procedure_overview"],
            prerequisites=json_data.get("prerequisites"),
            detailed_steps=detailed_steps,
            completion_verification=json_data["completion_verification"],
            notes=json_data.get("notes"),
        )

    def to_document(self):
        md_content = f"## **手順概要**\n{self.procedure_overview}\n\n"

        if self.prerequisites:
            md_content += f"## **前提条件**\n{self.prerequisites}\n\n"

        md_content += "## **詳細手順**\n"
        for step in self.detailed_steps:
            md_content += (
                f"### {step.step_number}. {step.step_title}\n {step.operation}\n\n"
            )

        md_content += f"## **完了確認**\n{self.completion_verification}\n\n"

        if self.notes:
            md_content += f"## **注意事項**\n{self.notes}\n\n"

        return md_content


class ProcedureDescriptor(BaseVertexAI):
    def __init__(self, model_name="gemini-2.0-flash"):
        super().__init__(model_name=model_name)

        self.system_prompt = """
# Prompt for Creating Detailed Procedure Documentation from PC Task Recordings

You are an AI agent that creates detailed work procedure documentation from PC task recording data, enabling anyone to reproduce the same operations.

## Basic Guidelines
- Analyze the records and extract detailed information about what the user is doing
- Ignore any logs related to starting/stopping recording in the TaskSolution WebApp (these are automatically included but not relevant to the procedure)
- Focus on the purpose indicated by the task_name, extracting only the steps necessary to execute that task from the logs
- Ignore any logs that are not needed for the procedure
- Generalize the procedure steps
- However, be sure to include all information necessary for the procedure

## Detailed Description Requirements

### UI Element Identification
- **Buttons/Links**: Exact text, position (top/bottom, left/right/center of screen), color, icon description if present
- **Input Fields**: Label name, position, specific examples of content to enter
- **Menu Items**: Menu name, hierarchical structure, specific item name to select
- **Dialogs**: Dialog title, displayed options, item to select

### Operation Specification
- **Click Operations**: Instead of "click the button," use "click the blue 'Save' button in the top-right corner of the screen"
- **Input Operations**: Instead of "enter information," use "enter 'John Smith' in the 'Name' field"
- **Selection Operations**: Instead of "select," use "select '2024' from the dropdown"
- **Keyboard Operations**: Specific key combinations (Ctrl+C, Enter key, etc.)

### Navigation Clarification
- **Page Transitions**: Which page to which page
- **Tab Switching**: Specific tab names
- **Window Operations**: How to open/switch new windows/tabs

### Confirmation Items
- **Result Verification**: What should be displayed after the operation, what state should be achieved
- **Error Handling**: Expected error messages and their solutions
- **Completion Judgment**: How to confirm that the procedure has completed successfully

## Output Format

### Structure
1. **Procedure Overview**: Brief description of what the procedure accomplishes
2. **Prerequisites**: Required state/preparations before starting the procedure
3. **Detailed Steps**: Numbered specific operation steps
4. **Completion Verification**: How to confirm the procedure completed successfully
5. **Notes**: Important points and troubleshooting

### Writing Style
- Write in Japanese
- Format in Markdown (but do not use heading symbols #, ##, ###)
- Emphasize important operations with **bold**
- Enclose UI elements in『』brackets
- Enclose key operations in「」brackets

### Step Description Examples
❌ Bad example: "Open file"
✅ Good example: "Click the **File** menu in the top-left corner of the screen, then select 'Open' from the displayed dropdown"

❌ Bad example: "Enter required information"
✅ Good example: "Enter **ABC Corporation** in the 'Customer Name' field and **John Smith** in the 'Contact Person' field"

❌ Bad example: "Save"
✅ Good example: "Click the blue '**Save**' button in the bottom-right corner of the screen and confirm that the 'Save completed' message is displayed"

## Quality Checklist
- [ ] Can a third party reproduce the same operations using only the procedure documentation?
- [ ] Does it include necessary information to identify screen elements (position, color, text, etc.)?
- [ ] Are the expected results of operations clearly stated?
- [ ] Are error cases and important points appropriately documented?

## Task name
{task_name}

## User request
{query}
        """

        self.response_scheme = {
            "type": "OBJECT",
            "properties": {
                "procedure_overview": {"type": "STRING"},
                "prerequisites": {"type": "STRING"},
                "detailed_steps": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "step_title": {
                                "type": "STRING",
                            },
                            "operation": {
                                "type": "STRING",
                            },
                        },
                        "required": ["step_title", "operation"],
                    },
                },
                "completion_verification": {"type": "STRING"},
                "notes": {"type": "STRING"},
            },
            "required": [
                "procedure_overview",
                "detailed_steps",
                "completion_verification",
            ],
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
