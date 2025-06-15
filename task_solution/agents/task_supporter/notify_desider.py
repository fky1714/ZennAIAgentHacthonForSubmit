import json
from pydantic import BaseModel, Field, validator
from typing import Dict, Any

from ..vertex_ai.base_vertex_ai import BaseVertexAI


class NotifyInfo(BaseModel):
    importance_level: int = Field(
        description="importance level of the support, 1-5, 5 being the most important"
    )
    is_duplicate: bool = Field(
        description="Boolean of a notify message is included logs"
    )

    @validator("importance_level")
    def validate_importance_level(cls, v):
        """重要度レベルが1-5の範囲内であることを検証"""
        if not 1 <= v <= 5:
            raise ValueError("importance_level must be between 1 and 5")
        return v

    @classmethod
    def from_json_data(cls, json_data: Dict[str, Any]) -> "NotifyInfo":
        return cls(
            importance_level=json_data["importance_level"],
            is_duplicate=json_data["is_duplicate"],
        )

    @property
    def should_notify(self) -> bool:
        """通知すべきかどうかを判定（重複でない かつ 重要度が3以上）"""
        return not self.is_duplicate and self.importance_level >= 4


class NotifyDesider(BaseVertexAI):
    def __init__(self, model_name="gemini-2.5-pro-preview-03-25"):
        super().__init__(model_name=model_name)
        self.system_prompt = """
You are a PC monitoring assistant.
Your task has two objectives:

Determine the importance level (1–5) of the input notification message

Check whether the same or similar message exists in past notification logs

Notification Importance Criteria
Level 5 – Critical
Risk of system failure, data loss, or hardware damage

Example: Disk usage has reached 99%, Power unit failure

Level 4 – Major
Service outages, severe security warnings

Example: nginx has stopped, Unauthorized access detected

Level 3 – Moderate
Partial functionality loss, repeated minor errors

Example: Backup failed (3rd attempt)

Level 2 – Minor
Temporary issues, minor delays, errors that have recovered

Example: Service response was delayed but has recovered

Level 1 – Informational
Routine operational messages or normal completion notices

Example: Scheduled scan completed successfully

Log Matching Criteria
“Logs” refer to past notification messages that were previously sent

Check if the current notification message matches or closely resembles a previous log entry
        """
        self.response_scheme = {
            "type": "OBJECT",
            "properties": {
                "importance_level": {
                    "type": "INTEGER",
                    "description": "importance level of the support, 1-5, 5 being the most important",
                },
                "is_duplicate": {
                    "type": "BOOLEAN",
                    "description": "Boolean of a notify message is included logs",
                },
            },
            "required": ["importance_level", "is_duplicate"],
        }

    def is_need_notify(self, support_info: dict, log_context: str) -> bool:
        query = f"## Target Support Message\n{support_info.get('message', '')}\n\n## Logs\n{log_context}"

        contents = [self.system_prompt, query]

        response = self.invoke(contents)
        notify_info = NotifyInfo.from_json_data(json.loads(response.text))
        return notify_info.should_notify
