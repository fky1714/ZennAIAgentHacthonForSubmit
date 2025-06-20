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
import urllib.request
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
            if (
                t.task_type != "休憩" and t.task_type != "離席"
            ):  # Exclude specific types
                type_durations[t.task_type] += t.duration

        if not type_durations:
            return ""

        labels = list(type_durations.keys())
        sizes = [td.total_seconds() / 60 for td in type_durations.values()]

        charts_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "static", "generated_charts"
        )
        os.makedirs(charts_dir, exist_ok=True)

        filename = f"pie_chart_{uuid.uuid4().hex}.png"
        filepath = os.path.join(charts_dir, filename)

        # より鮮やかで見やすい色のパレット
        colors = [
            "#FF6B6B",  # コーラルレッド
            "#4ECDC4",  # ターコイズ
            "#45B7D1",  # ブルー
            "#96CEB4",  # ミントグリーン
            "#FECA57",  # ゴールド
            "#FF9FF3",  # ピンク
            "#54A0FF",  # ライトブルー
            "#5F27CD",  # パープル
            "#00D2D3",  # シアン
            "#FF9F43",  # オレンジ
        ]

        font_name_to_use = None
        # URL from subtask description, with _COLON_ replaced
        font_download_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansjp/NotoSansJP-Regular.ttf"
        font_filename = "NotoSansJP-Regular.ttf"
        # Correctly determine temp_font_dir relative to the task_solution directory
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )  # This should be task_solution
        temp_font_dir = os.path.join(base_dir, "temp_fonts")
        local_font_path = os.path.join(temp_font_dir, font_filename)

        os.makedirs(temp_font_dir, exist_ok=True)
        print(f"Temp font directory: {temp_font_dir}")

        if not os.path.exists(local_font_path):
            print(
                f"Font {font_filename} not found locally. Attempting to download from {font_download_url}..."
            )
            try:
                actual_url = (
                    font_download_url  # This variable already has the correct URL.
                )

                # Create a request object with a User-Agent header
                req = urllib.request.Request(
                    actual_url,
                    data=None,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    },
                )

                with urllib.request.urlopen(req) as response, open(
                    local_font_path, "wb"
                ) as out_file:
                    if response.status == 200:
                        data = response.read()  # Read data from response
                        out_file.write(data)  # Write to file
                        print(f"Font downloaded successfully to {local_font_path}")
                    else:
                        print(
                            f"Error during download: Server responded with status {response.status}"
                        )
                        local_font_path = None  # Indicate download failure

            except Exception as e:
                print(f"Error downloading font: {e}")
                local_font_path = None
        else:
            print(f"Font {font_filename} found locally at {local_font_path}")

        # フォント設定の改善（より確実な方法）
        font_prop = None
        if local_font_path and os.path.exists(local_font_path):
            try:
                # FontPropertiesオブジェクトを直接使用
                font_prop = fm.FontProperties(fname=local_font_path)
                print(f"Successfully loaded font from: {local_font_path}")
            except Exception as e:
                print(f"Error loading downloaded font {local_font_path}: {e}")
                font_prop = None

        # フォントプロパティが取得できなかった場合のフォールバック
        if font_prop is None:
            try:
                # システムの日本語フォントを検索
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
                        print(f"Using system font: {font_name}")
                        break

                if font_prop is None:
                    # 最後の手段：利用可能なフォントから日本語対応フォントを探す
                    for af in available_fonts:
                        if any(
                            keyword in af.lower()
                            for keyword in ["noto", "cjk", "jp", "japanese"]
                        ):
                            font_prop = fm.FontProperties(family=af)
                            print(f"Found Japanese font: {af}")
                            break

            except Exception as e:
                print(f"Error finding system fonts: {e}")

        if font_prop is None:
            print("No Japanese font found, using default font")
            font_prop = fm.FontProperties()  # デフォルトフォント

        # グラフのサイズと品質を向上
        fig, ax = plt.subplots(figsize=(10, 8), dpi=100)

        # 円グラフの作成（フォントプロパティを直接指定）
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
            colors=colors[: len(labels)],  # ラベル数に応じて色を選択
            textprops={"fontproperties": font_prop, "fontsize": 12, "weight": "bold"},
            pctdistance=0.85,
        )

        # パーセンテージテキストの色を白に設定（視認性向上）
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_weight("bold")
            autotext.set_fontsize(11)
            autotext.set_fontproperties(font_prop)

        # ラベルテキストの設定
        for text in texts:
            text.set_fontsize(12)
            text.set_weight("bold")
            text.set_fontproperties(font_prop)

        ax.axis("equal")

        # タイトルの設定（フォントプロパティを指定）
        plt.title(
            "作業時間割合", fontsize=16, weight="bold", pad=20, fontproperties=font_prop
        )

        # 背景色を設定（オプション）
        fig.patch.set_facecolor("white")

        try:
            plt.tight_layout()
            plt.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="white")
            plt.close(fig)
            print(f"Pie chart saved successfully to {filepath}")
        except Exception as e:
            print(f"Error saving pie chart: {e}")
            return ""

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
