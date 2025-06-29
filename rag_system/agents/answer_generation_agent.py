from vertex_ai import BaseVertexAI

class AnswerGenerationAgent(BaseVertexAI):
    """
    参照情報とユーザーの質問に基づいて回答を生成するエージェント。
    ハルシネーションを抑制し、情報が見つからない場合はその旨を伝える。
    """
    def __init__(self, model_name: str = "gemini-pro", project: str = "your-gcp-project", location: str = "us-central1"):
        super().__init__(model_name, project, location)

    def predict(self, user_question: str, documents: list[str], **kwargs) -> str:
        """
        参照情報とユーザーの質問から回答を生成します。

        Args:
            user_question: ユーザーからの質問文。
            documents: 参照するドキュメントのリスト。
            **kwargs: BaseVertexAI.predict に渡す追加の引数。

        Returns:
            生成された回答文字列。
        """
        if not documents:
            # ダミーのBaseVertexAIがこの文字列を解釈して「情報なし」の応答をするようにする
            # 実際のLLMの場合は、プロンプトで情報がない場合の挙動を指示する
            simulated_llm_input_for_dummy = "回答生成プロンプト:\n関連情報なし"
            # return "参照できる情報がありませんでした。" # LLMを介さない場合の直接的な応答
        else:
            formatted_documents = "\n\n".join(
                [f"参照情報 {i+1}:\n{doc}" for i, doc in enumerate(documents)]
            )
            simulated_llm_input_for_dummy = f"""回答生成プロンプト:
以下の参照情報に厳密に基づいて、ユーザーの質問に回答してください。
参照情報に直接関連する情報が見つからない場合は、その旨を正直に伝えてください。決して推測や自身の知識で回答を補完しないでください。

参照情報:
{formatted_documents}

ユーザーの質問:
"{user_question}"

回答:
"""

        # 実際のLLM呼び出しの代わりに、スーパークラスのダミーpredictを使用
        # BaseVertexAIのダミーpredictはプロンプト内のキーワードに基づいて応答をシミュレート
        answer = super().predict(simulated_llm_input_for_dummy, **kwargs)
        return answer

if __name__ == '__main__':
    # 簡単なテスト
    agent = AnswerGenerationAgent()

    # ケース1: 関連情報がある場合
    q1 = "システムAのバグ修正はいつ行われましたか？"
    docs1 = [
        "作業レポート1: システムAのバグ修正を実施しました。完了日: 2023-10-26。",
        "作業レポート2: システムBのパフォーマンス改善を行いました。",
    ]
    ans1 = agent.predict(q1, docs1)
    print(f"質問1: \"{q1}\"")
    print(f"参照情報1: {docs1}")
    print(f"回答1: {ans1}") # 期待: "システムAのバグ修正は2023-10-26に実施されました。" (ダミーなので固定応答)
    print("-" * 20)

    # ケース2: 関連情報がない場合 (ドキュメント自体はあるが、質問に合致しない)
    q2 = "新機能Cのリリース日はいつですか？"
    docs2 = [
        "作業レポート1: システムAのバグ修正を実施しました。",
        "作業レポート2: システムBのパフォーマンス改善を行いました。",
    ]
    ans2 = agent.predict(q2, docs2)
    print(f"質問2: \"{q2}\"")
    print(f"参照情報2: {docs2}")
    print(f"回答2: {ans2}") # 期待: "参照情報に該当する情報は見つかりませんでした。" (ダミーなので固定応答)
    print("-" * 20)

    # ケース3: ドキュメントが空の場合
    q3 = "システムXの状況を教えてください。"
    docs3 = []
    ans3 = agent.predict(q3, docs3)
    print(f"質問3: \"{q3}\"")
    print(f"参照情報3: {docs3}")
    print(f"回答3: {ans3}") # 期待: "参照情報に該当する情報は見つかりませんでした。" (ダミーなので固定応答)
    print("-" * 20)

    # ケース4: 曖昧な質問で、部分的に合致する情報がある場合
    q4 = "バグ修正について教えて"
    docs4 = [
        "作業レポート1: システムAのバグ修正を実施しました。完了日: 2023-10-26。",
        "手順書X: バグ報告の手順について。",
    ]
    ans4 = agent.predict(q4, docs4)
    print(f"質問4: \"{q4}\"")
    print(f"参照情報4: {docs4}")
    print(f"回答4: {ans4}") # 期待: "システムAのバグ修正が2023-10-26に実施されました。また、バグ報告の手順に関する情報があります。" (ダミーなので固定応答)
    print("-" * 20)
