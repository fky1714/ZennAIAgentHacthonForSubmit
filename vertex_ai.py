class BaseVertexAI:
    def __init__(self, model_name: str, project: str, location: str):
        self.model_name = model_name
        self.project = project
        self.location = location
        print(f"DEBUG: BaseVertexAI initialized with model_name={model_name}, project={project}, location={location}")

    def predict(self, prompt: str, **kwargs) -> str:
        # This is a dummy predict method.
        # In a real scenario, this would interact with the Vertex AI API.
        print(f"DEBUG: BaseVertexAI.predict called with prompt:\n{prompt}")
        print(f"DEBUG: BaseVertexAI.predict kwargs: {kwargs}")

        # Simulate different outputs based on keywords in the prompt
        if "情報種別判断プロンプト" in prompt:
            if "これは「作業レポート」に関する質問です。" in prompt:
                return "作業レポート"
            elif "これは「作業手順書」に関する質問です。" in prompt:
                return "作業手順書"
            elif "これは「一般知識」に関する質問です。" in prompt:
                return "一般知識"
            else:
                # Fallback for safety, though _determine_type_for_dummy should cover cases
                print("DEBUG: BaseVertexAI.predict - 情報種別プロンプトでキーワード見つからず。デフォルト「一般知識」")
                return "一般知識"
        elif "回答生成プロンプト" in prompt:
            if "関連情報なし" in prompt: # AnswerGenerationAgentがこのキーワードを付与することを想定
                return "参照情報に該当する情報は見つかりませんでした。"
            return "これはダミーの回答です。提供された情報に基づいています。"

        print("DEBUG: BaseVertexAI.predict - 未知のプロンプトタイプ。デフォルト「Unknown」")
        return "Unknown prompt type for dummy BaseVertexAI"

    async def predict_async(self, prompt: str, **kwargs) -> str:
        # This is a dummy async predict method.
        print(f"DEBUG: BaseVertexAI.predict_async called with prompt:\n{prompt}")
        print(f"DEBUG: BaseVertexAI.predict_async kwargs: {kwargs}")
        if "情報種別判断プロンプト" in prompt:
            if "これは「作業レポート」に関する質問です。" in prompt:
                return "作業レポート"
            elif "これは「作業手順書」に関する質問です。" in prompt:
                return "作業手順書"
            elif "これは「一般知識」に関する質問です。" in prompt:
                return "一般知識"
            else:
                return "一般知識" # Fallback
        elif "回答生成プロンプト" in prompt:
            if "関連情報なし" in prompt:
                return "参照情報に該当する情報は見つかりませんでした。(async)"
            return "これはダミーの非同期回答です。提供された情報に基づいています。"
        return "Unknown prompt type for dummy BaseVertexAI (async)"
