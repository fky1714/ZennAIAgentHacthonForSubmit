from vertex_ai import BaseVertexAI

class InformationTypeAgent(BaseVertexAI):
    """
    ユーザーの質問から参照する情報種別（作業レポート、作業手順書、一般知識）を判断するエージェント。
    """
    def __init__(self, model_name: str = "gemini-pro", project: str = "your-gcp-project", location: str = "us-central1"):
        super().__init__(model_name, project, location)

    def predict(self, user_question: str, **kwargs) -> str:
        """
        ユーザーの質問を分析し、適切な情報種別を返します。

        Args:
            user_question: ユーザーからの質問文。
            **kwargs: BaseVertexAI.predict に渡す追加の引数。

        Returns:
            "作業レポート", "作業手順書", "一般知識" のいずれかの文字列。
        """
        prompt = f"""ユーザーからの以下の質問は、どの情報種別を参照すべきか判断してください。
回答は「作業レポート」、「作業手順書」、「一般知識」のいずれか一つのみで答えてください。

質問:
"{user_question}"

情報種別:
"""
        # 実際のLLM呼び出しの代わりに、スーパークラスのダミーpredictを使用します。
        # このダミーpredictはプロンプト内のキーワードに基づいて応答をシミュレートします。
        # 実際のシナリオでは、LLMがこのプロンプトに基づいて判断します。
        # ここでは "情報種別" というキーワードをプロンプトに含めているため、
        # BaseVertexAIのダミー実装がそれに応じて応答します。
        # また、質問内容に応じてダミーが適切な判断をするように、質問内容をプロンプトに含めます。
        simulated_llm_input_for_dummy = f"""情報種別判断プロンプト:
{prompt}
ユーザーの質問内容から判断すると、これは「{self._determine_type_for_dummy(user_question)}」に関する質問です。
"""
        predicted_type = super().predict(simulated_llm_input_for_dummy, **kwargs)

        # LLMの出力が期待する形式であることを確認（実際のLLMではより厳密なパースが必要になる場合がある）
        if predicted_type not in ["作業レポート", "作業手順書", "一般知識"]:
            # 不明な場合は一般知識としてフォールバックするなどの戦略も考えられる
            print(f"警告: LLMからの情報種別が予期せぬ値です: {predicted_type}。'一般知識'として扱います。")
            return "一般知識"
        return predicted_type

    def _determine_type_for_dummy(self, user_question: str) -> str:
        """
        BaseVertexAIのダミーpredictメソッドが適切な応答を返すように、
        ユーザーの質問内容に基づいてキーワードを推測するヘルパーメソッド。
        """
        question_lower = user_question.lower()
        if "レポート" in question_lower or "報告" in question_lower or "結果" in question_lower or "バグ" in question_lower or "障害" in question_lower or "進捗" in question_lower:
            return "作業レポート"
        elif "手順" in question_lower or "方法" in question_lower or "やり方" in question_lower or "マニュアル" in question_lower or "ガイド" in question_lower:
            return "作業手順書"
        else:
            return "一般知識"

if __name__ == '__main__':
    # 簡単なテスト
    agent = InformationTypeAgent()

    q1 = "先週のシステムAのバグ修正報告書はどこにありますか？"
    type1 = agent.predict(q1)
    print(f"質問: \"{q1}\" -> 情報種別: {type1}") # 期待: 作業レポート

    q2 = "新しいプリンターの設定方法を教えてください。"
    type2 = agent.predict(q2)
    print(f"質問: \"{q2}\" -> 情報種別: {type2}") # 期待: 作業手順書

    q3 = "今日の天気は？"
    type3 = agent.predict(q3)
    print(f"質問: \"{q3}\" -> 情報種別: {type3}") # 期待: 一般知識

    q4 = "プロジェクトXの進捗について知りたい。"
    type4 = agent.predict(q4)
    print(f"質問: \"{q4}\" -> 情報種別: {type4}") # 期待: 作業レポート (進捗報告など)

    q5 = "データベースのバックアップ手順を教えて。"
    type5 = agent.predict(q5)
    print(f"質問: \"{q5}\" -> 情報種別: {type5}") # 期待: 作業手順書
