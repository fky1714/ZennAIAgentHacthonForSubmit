from collections import defaultdict
from datetime import datetime, timedelta
import json
from pydantic import BaseModel, Field
from typing import Dict, Any
from ..vertex_ai.base_vertex_ai import BaseVertexAI
import matplotlib
matplotlib.use('Agg') # Ensure matplotlib doesn't try to use a GUI backend
import matplotlib.pyplot as plt
import os
import uuid
# from collections import defaultdict # Already imported
# from datetime import timedelta # Already imported


class TimeTable(BaseModel):
    task_type: str = Field(description="タスクの種類")
    start_time: str = Field(description="開始時間 HH:MM形式")
    end_time: str = Field(description="終了時間 HH:MM形式")

    @property
    def duration(self):
        fmt = "%H:%M"
        st = datetime.strptime(self.start_time, fmt)
        et = datetime.strptime(self.end_time, fmt)
        delta = et - st
        if delta.total_seconds() < 0:
            delta += timedelta(days=1)
        return delta


class TimeTableList(BaseModel):
    time_table: list[TimeTable] = Field(description="タスクの時間割のリスト")

    @classmethod
    def from_json_data(cls, json_data: Dict[str, Any]) -> "TimeTableList":
        # タイムテーブルデータを変換
        time_table = []
        for time_table_data in json_data["time_table"]:
            task = TimeTable(
                task_type=time_table_data["task_type"],
                start_time=time_table_data["start_time"],
                end_time=time_table_data["end_time"],
            )
            time_table.append(task)

        # クラスメソッドからインスタンスを作成
        return cls(time_table=time_table)

    def to_str(self) -> str:
        return "\n".join(
            [
                f"- {t.task_type} [startTime:: {t.start_time}]  [endTime:: {t.end_time}]"
                for t in self.time_table
            ]
        )

    def _format_timedelta_jp(self, td: timedelta) -> str:
        total_minutes = int(td.total_seconds() // 60)
        hours, minutes = divmod(total_minutes, 60)
        return f"{hours}時間{minutes}分"

    def total_duration_by_type(self) -> str:
        type_durations = defaultdict(timedelta)
        all_task_dt = timedelta()
        for t in self.time_table:
            type_durations[t.task_type] += t.duration
            if t.task_type != "休憩" and t.task_type != "離席":
                all_task_dt += t.duration
        whole_task_duration = (
            f"**総作業時間**: {self._format_timedelta_jp(all_task_dt)}\n"
        )
        task_durations = "\n".join(
            [
                f"    {task_type}: {self._format_timedelta_jp(duration)}"
                for task_type, duration in type_durations.items()
            ]
        )
        return f"{whole_task_duration}\n{task_durations}"

    def generate_pie_chart_path(self) -> str:
        type_durations = defaultdict(timedelta)
        for t in self.time_table:
            # Exclude '休憩' (Rest) and '離席' (Away) from the chart
            if t.task_type != "休憩" and t.task_type != "離席":
                type_durations[t.task_type] += t.duration

        if not type_durations:
            return "" # Return empty if no data to plot

        labels = type_durations.keys()
        # Convert timedelta objects to total minutes for plotting
        sizes = [td.total_seconds() / 60 for td in type_durations.values()]

        # Create the directory for charts if it doesn't exist
        charts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static", "generated_charts")
        os.makedirs(charts_dir, exist_ok=True)

        # Generate unique filename
        filename = f"pie_chart_{uuid.uuid4().hex}.png"
        filepath = os.path.join(charts_dir, filename)

        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        plt.title("作業時間割合") # Title: "Work Time Percentage"

        try:
            plt.savefig(filepath)
            plt.close(fig) # Close the figure to free memory
        except Exception as e:
            # Handle potential errors during saving (e.g. permissions)
            # For now, we'll print an error and return an empty path
            print(f"Error saving pie chart: {e}")
            return ""

        # Return the web-accessible path
        return f"/static/generated_charts/{filename}"


class TimeTableMaker(BaseVertexAI):
    def __init__(self, model_name="gemini-2.5-pro-preview-03-25"):
        super().__init__(model_name=model_name)
        self.system_prompt = """
        あなたは、ユーザーの作業ログを分析し、タスクの時間割を作成するAIアシスタントです。
        ユーザーが行った作業の詳細なログと作業種別を受け取り、いつからいつまでどのタスクを行っていたかを示す時間割を作成してください。
        """
        self.response_scheme = {
            "type": "OBJECT",
            "properties": {
                "time_table": {
                    "type": "ARRAY",
                    "description": "タスクの時間割のリスト",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "task_type": {
                                "type": "STRING",
                                "description": "タスクの種類",
                            },
                            "start_time": {
                                "type": "STRING",
                                "description": "開始時間 HH:MM形式",
                            },
                            "end_time": {
                                "type": "STRING",
                                "description": "終了時間 HH:MM形式",
                            },
                        },
                        "required": ["task_type", "start_time", "end_time"],
                    },
                }
            },
            "required": ["time_table"],
        }

    def make_time_table(self, log_text: str, task_type: str) -> TimeTableList:
        """
        :param log_text: 作業ログ
        :param task_type: タスクの種類
        :return: 時間割 (dict)
        """
        query = f"## 作業ログ{log_text}\n\n## タスクの種類{task_type}"
        contents = [self.system_prompt, query]

        response = self.invoke(contents)
        time_table_list = TimeTableList.from_json_data(json.loads(response.text))
        return time_table_list
