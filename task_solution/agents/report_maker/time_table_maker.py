from collections import defaultdict
from datetime import datetime, timedelta
import json
from pydantic import BaseModel, Field
from typing import Dict, Any
from ..vertex_ai.base_vertex_ai import BaseVertexAI
import matplotlib

matplotlib.use("Agg")  # Ensure matplotlib doesn't try to use a GUI backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import uuid


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
            # 「離席」は総作業時間に含めないが、「休憩」は場合による（ここでは集計上は含める）
            if t.task_type != "離席":
                # グラフ表示対象としての作業時間とは別に、表示用の総作業時間には休憩も含めて良いか検討
                # ここでは元々のロジックを踏襲し、「休憩」と「離席」を除いたものを「総作業時間」とする
                if t.task_type != "休憩":
                    all_task_dt += t.duration
        whole_task_duration = (
            f"**総作業時間**: {self._format_timedelta_jp(all_task_dt)}\n"
        )
        # 「離席」は作業時間の内訳に表示しない
        task_durations_list = []
        for task_type, duration in type_durations.items():
            if task_type != "離席":
                task_durations_list.append(
                    f"    {task_type}: {self._format_timedelta_jp(duration)}"
                )

        task_durations = "\n".join(task_durations_list)
        return whole_task_duration + task_durations

    def get_task_types_for_chart(self) -> dict[str, timedelta]:
        """グラフ表示対象となる作業種別とその合計時間を取得する"""
        type_durations = defaultdict(timedelta)
        for t in self.time_table:
            if t.task_type != "離席":  # 「離席」のみ除外
                type_durations[t.task_type] += t.duration
        return dict(type_durations)

    def generate_pie_chart_path(self) -> str:
        try:
            # フォントキャッシュを強制的に再構築
            fm._load_fontmanager(try_read_cache=False)
            print("Successfully reloaded font manager.")
        except Exception as e:
            print(f"Error reloading font manager: {e}")

        type_durations_for_chart = self.get_task_types_for_chart()

        if not type_durations_for_chart:
            return ""

        labels = list(type_durations_for_chart.keys())
        sizes = [td.total_seconds() / 60 for td in type_durations_for_chart.values()]

        charts_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "static", "generated_charts"
        )
        os.makedirs(charts_dir, exist_ok=True)

        filename = f"pie_chart_{uuid.uuid4().hex}.png"
        filepath = os.path.join(charts_dir, filename)

        colors = [
            "#FF6B6B",
            "#4ECDC4",
            "#45B7D1",
            "#96CEB4",
            "#FECA57",
            "#FF9FF3",
            "#54A0FF",
            "#5F27CD",
            "#00D2D3",
            "#FF9F43",
        ]

        available_fonts = [f.name for f in fm.fontManager.ttflist]
        japanese_fonts = [
            "Noto Sans CJK JP",
            "NotoSansCJK-Regular",
            "Hiragino Sans",
            "Yu Gothic",
            "Meiryo",
            "Takao",
            "DejaVu Sans",
        ]

        for font_name in japanese_fonts:
            if any(font_name.lower() in af.lower() for af in available_fonts):
                font_prop = fm.FontProperties(family=font_name)
                print(f"Using system fallback font: {font_name}")
                break

        # Adjust chart size and text sizes
        fig, ax = plt.subplots(
            figsize=(7, 5), dpi=100
        )  # Smaller figure size, adjusted aspect ratio

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=colors[: len(labels)],
            textprops={
                "fontproperties": font_prop,
                "fontsize": 10,
                "weight": "normal",
            },  # Smaller label font size
            pctdistance=0.80,  # Adjust pctdistance if labels overlap
        )

        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_weight("bold")
            autotext.set_fontsize(9)  # Smaller percentage font size
            autotext.set_fontproperties(font_prop)

        for text in texts:
            text.set_fontsize(10)  # Smaller label text
            # text.set_weight("bold") # Making labels normal weight for potentially cleaner look
            text.set_fontproperties(font_prop)

        ax.axis("equal")
        plt.title(
            "作業時間割合",
            fontsize=14,
            weight="bold",
            pad=15,
            fontproperties=font_prop,  # Smaller title
        )
        fig.patch.set_facecolor("white")

        try:
            plt.tight_layout()  # Apply tight_layout before savefig
            plt.savefig(
                filepath, dpi=100, bbox_inches="tight", facecolor="white"
            )  # Adjusted savefig dpi
            plt.close(fig)
            print(f"Pie chart saved successfully to {filepath}")
            if os.path.exists(filepath):
                print(f"File check inside generate_pie_chart_path: {filepath} exists.")
            else:
                print(
                    f"File check inside generate_pie_chart_path: {filepath} DOES NOT exist."
                )
        except Exception as e:
            print(f"Error saving pie chart: {e}")
            return ""

        return f"/static/generated_charts/{filename}"


class TimeTableMaker(BaseVertexAI):
    def __init__(self):
        super().__init__()
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
