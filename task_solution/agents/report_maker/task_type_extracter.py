import json
from pydantic import BaseModel, Field
from typing import Dict, Any


from ..vertex_ai.base_vertex_ai import BaseVertexAI


class TaskType(BaseModel):
    type: str = Field(description="タスクの種類")


class TaskTypeList(BaseModel):
    task_types: list[TaskType] = Field(description="タスクの種類のリスト")

    @classmethod
    def from_json_data(cls, json_data: Dict[str, Any]) -> "TaskTypeList":
        # タスクタイプデータを変換
        task_types = []
        for task_type_data in json_data["task_types"]:
            task_type = TaskType(type=task_type_data["type"])
            task_types.append(task_type)

        # クラスメソッドからインスタンスを作成
        return cls(task_types=task_types)

    def to_str(self) -> str:
        return ", ".join([task_type.type for task_type in self.task_types])


class TaskTypeExtractor(BaseVertexAI):
    def __init__(self, model_name="gemini-2.5-pro-preview-03-25"):
        super().__init__(model_name=model_name)
        self.system_prompt = """
        あなたは、ユーザーの作業ログを分析し、タスクの種類を特定するAIアシスタントです。
        ユーザーが行った作業の詳細なログを受け取り、その中からタスクの種類をすべて抽出してください。
        どういった種類の作業をしていたかを知りたいだけなので、重複なし、順不同のリストを出力してください。

        以下のタスクの種類を事前に定義しますが、作業内容に応じて柔軟に分類してください
        - 文書作成
        - コミュニケーション
        - 調査
        - コーディング
        - デザイン
        - 創作
        - 学習
        - プロジェクト管理
        - 会議
        - 動画編集
        - 休憩
        - 離席
        - その他

        PCで何もしていないと判断できる場合は"離席"と答えてください。
        """
        self.response_scheme = {
            "type": "OBJECT",
            "properties": {
                "task_types": {
                    "type": "ARRAY",
                    "description": "タスクの種類のリスト",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "type": {"type": "STRING", "description": "タスクの種類"}
                        },
                        "required": ["type"],
                    },
                }
            },
            "required": ["task_types"],
        }

    def extract_task_type(self, log_text: str) -> TaskTypeList:
        query = f"{log_text}"
        contents = [self.system_prompt, query]

        response = self.invoke(contents)
        output = TaskTypeList.from_json_data(json.loads(response.text))
        return output
