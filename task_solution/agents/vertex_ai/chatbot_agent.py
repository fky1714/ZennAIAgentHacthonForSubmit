from .base_vertex_ai import BaseVertexAI

from utils.logger import Logger


class ChatbotAgent(BaseVertexAI):
    def __init__(
        self, model_name="gemini-2.5-pro-preview-03-25"
    ):  # モデル名を "gemini-pro" に変更
        super().__init__(model_name)
        self.logger = Logger(name=self.__class__.__name__).get_logger()

    def generate_response(self, user_message: str) -> str:
        """
        ユーザーメッセージに基づいて応答を生成します。
        """
        self.logger.info(f"Generating response for: {user_message}")

        # Vertex AIのモデルに渡すコンテンツを作成
        # プロンプトは適宜調整してください
        prompt = f"""ユーザーからの以下のメッセージに対して、親切かつ簡潔に応答してください。

ユーザーメッセージ: {user_message}

あなたの応答:"""

        try:
            generative_model = self.model
            response = generative_model.generate_content(prompt)

            self.logger.info(f"Raw response from Vertex AI: {response}")

            if response.candidates and response.candidates[0].content.parts:
                bot_reply = "".join(
                    part.text
                    for part in response.candidates[0].content.parts
                    if hasattr(part, "text")
                )
                if not bot_reply.strip():  # 空の応答やスペースのみの応答をチェック
                    bot_reply = "申し訳ありません、うまく応答を生成できませんでした。"
            else:
                bot_reply = "申し訳ありません、応答を取得できませんでした。"
                self.logger.warning(
                    f"Could not get a valid response structure. Response: {response}"
                )

        except Exception as e:
            self.logger.error(f"Error during Vertex AI call: {e}")
            bot_reply = "申し訳ありません、技術的な問題が発生しました。"
            import traceback

            self.logger.error(traceback.format_exc())

        self.logger.info(f"Generated bot reply: {bot_reply}")
        return bot_reply


if __name__ == "__main__":
    # 簡単なテスト用
    agent = ChatbotAgent()

    # テストメッセージ
    test_messages = ["こんにちは", "今日の天気は？", "ありがとう", "何か面白い話をして"]

    for msg in test_messages:
        print(f"ユーザー: {msg}")
        reply = agent.generate_response(msg)
        print(f"ボット: {reply}")
        print("-" * 20)

    # 環境変数GCP_PROJECTとGCP_LOCATIONが設定されていることを確認してください。
    # 例:
    # export GCP_PROJECT="your-gcp-project-id"
    # export GCP_LOCATION="us-central1"
    # python -m agents.vertex_ai.chatbot_agent
    # (task_solution ディレクトリからの実行を想定)
    # (ImportError回避のため、PYTHONPATH=. python task_solution/agents/vertex_ai/chatbot_agent.py のように実行する可能性あり)
