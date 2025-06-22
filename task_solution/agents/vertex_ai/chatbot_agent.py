from .base_vertex_ai import BaseVertexAI
# from vertexai.generative_models import GenerativeModel, Part, GenerationConfig # BaseVertexAIでimport済みなので不要かも
from utils.logger import Logger

class ChatbotAgent(BaseVertexAI):
    def __init__(self, model_name="gemini-pro"): # モデル名を "gemini-pro" に変更
        super().__init__(model_name)
        self.logger = Logger(name=self.__class__.__name__).get_logger()
        # Chatbot用のresponse_schemeは単純なテキスト応答なので、設定しないか、
        # もしJSONでラップするならここで定義します。
        # 今回は単純なテキスト応答と仮定し、BaseVertexAIのresponse_schemeは使用しません。
        # self.response_scheme = ...

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
            # BaseVertexAIのgeneration_configはJSON出力を想定しているため、
            # テキスト応答の場合は直接model.generate_contentを呼び出すか、
            # generation_configをオーバーライドする必要があります。
            # ここでは、テキスト応答用にconfigを調整せずに呼び出します。
            # 必要であれば、BaseVertexAI側でテキスト応答用のメソッドを用意するか、
            # このクラスでgeneration_configを上書きしてください。

            # response = self.model.generate_content(prompt) # generation_configなしで呼び出し

            # BaseVertexAIのinvokeメソッドを使用する場合、response_schemeが設定されていると
            # JSON形式での応答を期待します。テキストベースのチャットボットでは、
            # response_schemeをNoneにするか、テキスト応答用の別の設定でinvokeを呼び出す必要があります。
            # ここでは、response_schemeがNoneであると仮定してinvokeを呼び出します。
            # もしBaseVertexAIのresponse_schemeが固定でJSONなら、この呼び出し方はエラーになります。

            # テキスト応答を得るために、BaseVertexAIのgeneration_configを使わずに直接呼び出す
            generative_model = self.model
            response = generative_model.generate_content(prompt)

            self.logger.info(f"Raw response from Vertex AI: {response}")

            # レスポンスのテキスト部分を取得
            # 応答の構造はモデルや設定によって異なる場合があるので、適切な処理が必要です。
            # 以下は一般的なGeminiモデルの応答からのテキスト抽出の例です。
            if response.candidates and response.candidates[0].content.parts:
                bot_reply = "".join(part.text for part in response.candidates[0].content.parts if hasattr(part, 'text'))
                if not bot_reply.strip(): # 空の応答やスペースのみの応答をチェック
                    bot_reply = "申し訳ありません、うまく応答を生成できませんでした。"
            else:
                bot_reply = "申し訳ありません、応答を取得できませんでした。"
                self.logger.warning(f"Could not get a valid response structure. Response: {response}")

        except Exception as e:
            self.logger.error(f"Error during Vertex AI call: {e}")
            bot_reply = "申し訳ありません、技術的な問題が発生しました。"
            import traceback
            self.logger.error(traceback.format_exc())

        self.logger.info(f"Generated bot reply: {bot_reply}")
        return bot_reply

if __name__ == '__main__':
    # 簡単なテスト用
    agent = ChatbotAgent()

    # テストメッセージ
    test_messages = [
        "こんにちは",
        "今日の天気は？",
        "ありがとう",
        "何か面白い話をして"
    ]

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
