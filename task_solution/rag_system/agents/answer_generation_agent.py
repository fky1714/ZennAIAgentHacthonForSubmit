# from vertex_ai import BaseVertexAI # ダミーのBaseVertexAI
from agents.vertex_ai.base_vertex_ai import BaseVertexAI  # 実際のBaseVertexAI
from vertexai.generative_models import GenerationResponse
import os


class AnswerGenerationAgent(BaseVertexAI):
    """
    参照情報とユーザーの質問に基づいて回答を生成するエージェント。
    ハルシネーションを抑制し、情報が見つからない場合はその旨を伝える。
    実際の BaseVertexAI を使用する。
    """

    def __init__(self, model_name: str = "gemini-2.5-pro"):  # モデル名は適宜調整
        super().__init__(model_name)
        # 応答形式はプレーンテキストを期待するため、response_scheme や generation_config の調整は
        # InformationTypeAgent と同様に、ひとまず行わない。
        pass

    def predict(self, user_question: str, documents: list[str]) -> str:
        """
        参照情報とユーザーの質問から回答を生成します。

        Args:
            user_question: ユーザーからの質問文。
            documents: 参照するドキュメントのリスト。

        Returns:
            生成された回答文字列。
        """
        if not documents:
            # ドキュメントがない場合はLLMを呼び出さずに固定応答を返す
            # (QAWorkflow側でもドキュメントがない場合の処理はあるが、エージェントとしても対応)
            self.logger.info("ドキュメントが提供されなかったため、固定応答を返します。")
            return "参照できる関連情報が見つかりませんでした。"

        formatted_documents = "\n\n".join(
            [f"参照情報 {i+1}:\n{doc}" for i, doc in enumerate(documents)]
        )

        prompt = f"""以下の参照情報に厳密に基づいて、ユーザーの質問に簡潔に、マークダウン形式ではなくプレーンテキストで回答してください。
参照情報に直接関連する情報が見つからない場合は、「参照情報に該当する情報は見つかりませんでした。」と回答してください。
決して推測や自身の知識で回答を補完しないでください。

参照情報:
{formatted_documents}

ユーザーの質問:
"{user_question}"

回答:"""

        try:
            # generation_configを使わずに直接モデルを呼び出し、テキスト応答を期待
            response: GenerationResponse = self.model.generate_content(prompt)
            self.logger.info(f"Raw response from LLM for answer generation: {response}")
            answer = response.text.strip()
            if not answer:  # LLMが空の応答を返す場合
                self.logger.warning("LLMからの応答が空でした。")
                answer = "申し訳ありません、回答を生成できませんでした。"
        except Exception as e:
            self.logger.error(f"Error during LLM call in AnswerGenerationAgent: {e}")
            answer = (
                "申し訳ありません、技術的な問題が発生し回答を生成できませんでした。"
            )

        return answer


if __name__ == "__main__":
    # 簡単なテスト (実際のVertex AI呼び出しが発生するため、認証と環境設定が必要)
    print(
        "AnswerGenerationAgentのテストを開始します。実際のVertex AI呼び出しが含まれます。"
    )
    print("GCP_PROJECTとGCP_LOCATION環境変数が設定されている必要があります。")

    if not os.getenv("GCP_PROJECT"):
        print(
            "エラー: GCP_PROJECT環境変数が設定されていません。テストをスキップします。"
        )
    else:
        agent = AnswerGenerationAgent()

        # ケース1: 関連情報がある場合
        q1 = "システムAのバグ修正はいつ行われましたか？"
        docs1 = [
            "作業レポート「バグ修正A」:\nシステムAの重大なバグXについて、修正作業を2023年10月26日に完了しました。",
            "作業レポート「パフォーマンス改善B」:\nシステムBのレスポンス速度改善のため、インデックスの追加とクエリの最適化を行いました。",
        ]
        print(f'\n質問1: "{q1}"')
        print(f"参照情報1: {docs1}")
        ans1 = agent.predict(q1, docs1)
        print(f"回答1: {ans1}")
        print("-" * 20)

        # ケース2: 関連情報がない場合 (ドキュメント自体はあるが、質問に合致しない)
        q2 = "新機能Cのリリース日はいつですか？"
        docs2 = [
            "作業レポート「バグ修正A」:\nシステムAの重大なバグXについて、修正作業を2023年10月26日に完了しました。",
            "作業手順書「システムBの起動方法」:\nシステムBを起動するには、まずサーバーにログインし、指定のスクリプトを実行します。",
        ]
        print(f'\n質問2: "{q2}"')
        print(f"参照情報2: {docs2}")
        ans2 = agent.predict(q2, docs2)
        print(
            f"回答2: {ans2}"
        )  # 期待: "参照情報に該当する情報は見つかりませんでした。"
        print("-" * 20)

        # ケース3: ドキュメントが空の場合
        q3 = "システムXの状況を教えてください。"
        docs3 = []
        print(f'\n質問3: "{q3}"')
        print(f"参照情報3: {docs3}")
        ans3 = agent.predict(q3, docs3)
        print(f"回答3: {ans3}")  # 期待: "参照できる関連情報が見つかりませんでした。"
        print("-" * 20)

        # ケース4: 曖昧な質問で、部分的に合致する情報があるかもしれない場合
        q4 = "バグ修正について何か情報はありますか？"
        docs4 = [
            "作業レポート「バグ修正A」:\nシステムAの重大なバグXについて、修正作業を2023年10月26日に完了しました。",
            "手順書「バグ報告手順」:\nバグを発見した場合、JIRAにチケットを作成し、再現手順とスクリーンショットを添付してください。",
        ]
        print(f'\n質問4: "{q4}"')
        print(f"参照情報4: {docs4}")
        ans4 = agent.predict(q4, docs4)
        print(f"回答4: {ans4}")
        print("-" * 20)
