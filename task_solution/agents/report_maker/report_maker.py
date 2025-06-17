import json
import os
from datetime import date
from pydantic import BaseModel, Field
from typing import Dict, Any

from ..vertex_ai.base_vertex_ai import BaseVertexAI
from ..report_maker.time_table_maker import TimeTableList


class Reference(BaseModel):
    title: str = Field(description="参考文献のタイトル")
    url: str = Field(description="参考文献のURL")


class ReportInfo(BaseModel):
    title: str = Field(description="一覧で表示されるレポートのタイトル 30文字以内")
    abstract: str = Field(description="レポートの概要")
    done_tasks: list[str] = Field(description="完了したタスクリスト")
    problems: list[str] = Field(description="遭遇した課題リス   ト")
    feedback: str = Field(description="作業内容に対する総評 よかった点、改善点など")
    references: list[Reference] = Field(description="参考文献のリスト")

    @classmethod
    def from_json_data(cls, json_data: Dict[str, Any]) -> "ReportInfo":
        # 参考文献データを変換
        references = []
        for ref_data in json_data["references"]:
            reference = Reference(title=ref_data["title"], url=ref_data["url"])
            references.append(reference)

        today = date.today()
        formatted_date = today.strftime("%Y-%m-%d")

        # クラスメソッドからインスタンスを作成
        return cls(
            title=f"{formatted_date} {json_data['title']}",
            abstract=json_data["abstract"],
            done_tasks=json_data["done_tasks"],
            problems=json_data["problems"],
            feedback=json_data["feedback"],
            references=references,
        )

    def done_tasks_to_str(self) -> str:
        return "\n".join([f"- {task}" for task in self.done_tasks])

    def problems_to_str(self) -> str:
        return "\n".join([f"- {problem}" for problem in self.problems])

    def to_markdown(self, time_table_list: TimeTableList) -> str:
        template_path = os.path.join(os.path.dirname(__file__), "report_template.md")
        with open(template_path, "r", encoding="utf-8") as f:
            report_template = f.read()
        return report_template.format(
            abstract=self.abstract,
            done_tasks=self.done_tasks_to_str(),
            problems=self.problems_to_str(),
            feedback=self.feedback,
            task_duration=time_table_list.total_duration_by_type(),
        )


class ReportMaker(BaseVertexAI):
    def __init__(self, model_name="gemini-2.5-pro-preview-03-25"):
        super().__init__(model_name=model_name)
        self.system_prompt = """
        あなたは、ユーザーの作業ログを分析し、作業レポートを作成するAIアシスタントです。
        ユーザーが行った作業の詳細なログを受け取り、その中から作業レポートに必要な情報を日本語で作成してください。

        ## 概要
        - 作業の概要を簡潔にまとめてください。
        - どのような作業を行ったのか、全体的な流れを説明してください。

        ## 完了したタスク
        - 完了したタスクをリスト形式で列挙してください。
        - どのタスクが完了したのか、具体的に記載してください。

        ## 課題
        - 作業中に遭遇した課題をリスト形式で列挙してください。
        - どのような問題が発生したのか、具体的に記載してください。
        - 課題が解決された場合は、その解決方法も記載してください。
        - なければ"特になし"と記載してください。

        ## フィードバック
        - 作業内容に対する総評を記載してください。
        - よかった点、改善点などを具体的に記載してください。
        - 必ず次の作業に活かせるようなフィードバックをしてください。

        !!出力フォーマット!!
        - markdown形式で出力すること
        - ただし、使用できる見出しレベルは####から
        """
        self.response_scheme = {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "一覧で表示されるレポートのタイトル 30文字以内",
                },
                "abstract": {"type": "STRING", "description": "レポートの概要"},
                "done_tasks": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "完了したタスクリスト",
                },
                "problems": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "遭遇した課題リスト",
                },
                "feedback": {
                    "type": "STRING",
                    "description": "作業内容に対する総評 よかった点、改善点など",
                },
                "references": {
                    "type": "ARRAY",
                    "description": "参考文献のリスト",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "title": {
                                "type": "STRING",
                                "description": "参考文献のタイトル",
                            },
                            "url": {"type": "STRING", "description": "参考文献のURL"},
                        },
                        "required": ["title", "url"],
                    },
                },
            },
            "required": [
                "title",
                "abstract",
                "done_tasks",
                "problems",
                "feedback",
                "references",
            ],
        }

    def make_report(self, log_text: str) -> ReportInfo:
        """
        :param log_text: ログ
        :return: 作業レポート (dict)
        """
        query = f"## 作業ログ\n{log_text}\n\n"
        contents = [self.system_prompt, query]

        response = self.invoke(contents)
        output = ReportInfo.from_json_data(json.loads(response.text))
        return output
