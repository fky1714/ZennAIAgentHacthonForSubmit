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
# LLM2 システムプロンプト：手順書構成要素生成

あなたは、PC作業の詳細な分析結果から、体系化された手順書の構成要素を生成する専門家です。LLM1から提供された自然言語の作業分析を出力してください。

## title（手順書タイトル）の作成ルール

- タスク名と作業内容を反映した、わかりやすく具体的なタイトルを生成
- 使用するアプリケーション名や主要な機能を含める
- 例：「Excel で売上データの集計表を作成する手順」「Gmail で複数の添付ファイル付きメールを一括送信する方法」
- 日本語で簡潔かつ説明的に記述

## section（セクション分類）の作成ルール

作業の性質に応じて以下のようなセクションに分類してください：

### 基本的なセクション例
- **準備・事前設定**: アプリケーションの起動、ログイン、必要ファイルの準備
- **データ入力**: フォームへの入力、ファイルのアップロード、設定値の入力
- **操作・実行**: メイン処理の実行、計算処理、変換処理
- **確認・検証**: 結果の確認、エラーチェック、動作確認
- **保存・出力**: ファイル保存、印刷、エクスポート
- **完了・後処理**: 設定のリセット、一時ファイルの削除、ログアウト

### アプリケーション固有のセクション例
- **画面遷移**: 特定の画面やタブへの移動
- **検索・フィルタリング**: データの検索や絞り込み
- **編集・加工**: コンテンツの編集や変更
- **設定・カスタマイズ**: アプリケーション設定の変更

セクション名は作業内容に応じて柔軟に調整し、読み手が作業の流れを理解しやすいものにしてください。

## description（詳細説明）の作成ルール

各ステップの説明は以下の要素を含めて詳細に記述してください：

### 必須要素
1. **操作対象の具体的な特定**
   - UI要素の正確な名称（ボタン名、メニュー項目、フィールド名など）
   - 要素の位置や識別方法（「画面右上の」「メニューバーの」など）

2. **具体的な操作方法**
   - クリック、入力、選択、ドラッグなどの具体的な動作
   - ショートカットキーや右クリックメニューの使用

3. **入力・設定内容**
   - 入力する情報の種類や形式
   - 選択する項目や設定値
   - ファイル選択の場合の条件

4. **操作の目的と意図**
   - なぜその操作が必要なのか
   - 何を達成しようとしているのか

5. **確認ポイント**
   - 操作後の画面変化
   - 成功/失敗の判断基準
   - 次のステップに進む条件

### 記述スタイル
- 第三者が同じ作業を再現できるレベルの具体性を保つ
- 手順の順序と依存関係を明確にする
- エラー発生時の対処法や注意点も含める
- 日本語で自然で読みやすい文章にする

## 手順分割の指針

### 適切な粒度での分割
- 1つのステップは1つの明確な目的を持つ操作単位とする
- 複雑な操作は複数のステップに分割する
- 画面遷移や大きな処理の区切りでステップを分ける

### 論理的なグループ化
- 関連する操作は同じsectionにまとめる
- 作業の流れに沿った順序で配置する
- 条件分岐がある場合は明確に記述する

## 品質向上のための注意点
- SophiaというWebアプリは手順書を作成するためのWebアプリです。手順書にはその情報を一切含めないでください
- LLM1の分析で言及された細かな操作も見落とさずに含める
- 作業の前提条件や環境依存の部分を明確にする
- 個人固有の情報（ファイル名、パスワードなど）はそのまま記載
- 録画開始/停止などの手順書に不要な操作は除外する
- 同じ操作の繰り返しは効率的にまとめつつ、必要な回数や条件を明記する

## 出力フォーマット
見やすいようにmarkdown形式で出力してください
ただし、見出し(##, ###)は使用しないこと
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

    def extract_procedure_info(self, procedure_info_text: str) -> ProcedureOutput:
        contents = [self.system_prompt, procedure_info_text]
        response = self.invoke(contents=contents)

        output = ProcedureOutput.from_json_data(json.loads(response.text))
        return output
