# from vertex_ai import BaseVertexAI # ダミーのBaseVertexAI
from task_solution.agents.vertex_ai.base_vertex_ai import BaseVertexAI # 実際のBaseVertexAI
from vertexai.generative_models import GenerationResponse

class InformationTypeAgent(BaseVertexAI):
    """
    ユーザーの質問から参照する情報種別（作業レポート、作業手順書、一般知識）を判断するエージェント。
    実際の BaseVertexAI を使用する。
    """
    def __init__(self, model_name: str = "gemini-1.5-flash-001"): # モデル名は適宜調整
        super().__init__(model_name)
        # response_scheme を定義する場合
        # self.response_scheme = {
        #     "type": "object",
        #     "properties": {
        #         "information_type": {
        #             "type": "string",
        #             "description": "Identified information type. Must be one of '作業レポート', '作業手順書', or '一般知識'."
        #         }
        #     },
        #     "required": ["information_type"]
        # }
        # 今回はプレーンテキストでの応答を期待するため、response_scheme は設定しないか、
        # generation_config で text/plain を指定する。
        # BaseVertexAIのgeneration_configがデフォルトでapplication/jsonなので、
        # ここでオーバーライドするか、invoke時にconfigを渡さないようにする。
        # もしくは、BaseVertexAI側のgeneration_config自体を修正する。
        # シンプルにするため、invoke時にgeneration_configを渡さず、デフォルトのテキスト応答を期待する。
        pass


    def predict(self, user_question: str) -> str:
        """
        ユーザーの質問を分析し、適切な情報種別を返します。

        Args:
            user_question: ユーザーからの質問文。

        Returns:
            "作業レポート", "作業手順書", "一般知識" のいずれかの文字列。
        """
        prompt = f"""ユーザーからの質問がどの情報種別を参照すべきか、以下の優先順位で判断してください。
回答は「作業手順書」、「一般知識」、「作業レポート」のいずれか一つのみで、その文字列だけを返してください。

1. 質問が作業のやり方や操作方法など、手順に関する内容であれば「作業手順書」と判断してください。
   例：「〇〇のセットアップ方法を教えて」「△△の操作手順は？」

2. 上記に当てはまらず、質問が一般的な知識（天気、ニュース、歴史、科学など）や挨拶、雑談のような内容であれば「一般知識」と判断してください。
   例：「今日の天気は？」「東京の人口は？」「こんにちは」

3. 上記のいずれにも当てはまらない場合、それは業務報告、バグ、障害、進捗、結果などに関する内容である可能性が高いので「作業レポート」と判断してください。
   例：「先週のバグ修正報告は？」「プロジェクトXの進捗を教えて」「システムAの障害状況は？」

質問:
"{user_question}"

情報種別:"""

        try:
            # BaseVertexAIのinvokeメソッドはcontentsリストを受け取ることを想定しているかもしれないが、
            # GenerativeModel.generate_content は文字列も受け付ける。
            # base_vertex_ai.pyの実装では self.model.generate_content(contents, ...)となっているので、
            # contentsは generate_contentが期待する形式(文字列かリスト)である必要がある。
            # ここではプロンプト文字列を直接渡す。
            # response = self.invoke(prompt) # invokeがgeneration_configを使うので、JSON応答を期待してしまう

            # generation_configを使わずに直接モデルを呼び出し、テキスト応答を期待
            response: GenerationResponse = self.model.generate_content(prompt)

            self.logger.info(f"Raw response from LLM for info type: {response}")
            predicted_type = response.text.strip()

        except Exception as e:
            self.logger.error(f"Error during LLM call in InformationTypeAgent: {e}")
            # エラー時はデフォルトで「一般知識」またはより安全な値にフォールバック
            return "一般知識"


        # LLMの出力が期待する形式であることを確認
        valid_types = ["作業レポート", "作業手順書", "一般知識"]
        if predicted_type not in valid_types:
            self.logger.warning(f"LLMからの情報種別が予期せぬ値です: {predicted_type}。'一般知識'として扱います。")
            # ここでのフォールバックは、新しい種別判断ロジック（その他は作業レポート）と矛盾する可能性あり。
            # プロンプトでより厳密な指示が必要。
            # 一旦、最も安全な「一般知識」にしておくか、あるいはプロンプトの指示に従うことを期待する。
            # もし厳密に上記の3つ以外を返してほしくないなら、ここで強制的に変換するかエラーにする。
            # 今回は、もし想定外なら「一般知識」と扱う。
            return "一般知識"

        return predicted_type

    # _determine_type_for_dummy は不要になるので削除

if __name__ == '__main__':
    # 簡単なテスト (実際のVertex AI呼び出しが発生するため、認証と環境設定が必要)
    # GOOGLE_APPLICATION_CREDENTIALS, GCP_PROJECT, GCP_LOCATION
    print("InformationTypeAgentのテストを開始します。実際のVertex AI呼び出しが含まれます。")
    print("GCP_PROJECTとGCP_LOCATION環境変数が設定されている必要があります。")

    if not os.getenv("GCP_PROJECT"):
        print("エラー: GCP_PROJECT環境変数が設定されていません。テストをスキップします。")
    else:
        agent = InformationTypeAgent()

        test_questions = {
            "先週のシステムAのバグ修正報告書はどこにありますか？": "作業レポート",
            "新しいプリンターの設定方法を教えてください。": "作業手順書",
            "今日の天気は？": "一般知識",
            "プロジェクトXの進捗について知りたい。": "作業レポート", # 新しいロジックでは作業レポートになるはず
            "データベースのバックアップ手順を教えて。": "作業手順書",
            "東京の人口は？": "一般知識",
            "このソフトウェアのライセンスについて教えて。": "作業レポート", # その他なので作業レポート
            "PCのメモリ増設の手順を教えてほしい": "作業手順書",
        }

        for q, expected_type in test_questions.items():
            print(f"\n質問: \"{q}\"")
            predicted = agent.predict(q)
            print(f"  期待される種別: {expected_type}")
            print(f"  予測された種別: {predicted}")
            if predicted == expected_type:
                print("  結果: OK")
            else:
                print(f"  結果: NG (期待値と異なります)")
