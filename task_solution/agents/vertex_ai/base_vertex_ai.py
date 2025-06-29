import os
import json
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from google.genai import types, Client # この行は現状使われていないようなので、後で削除検討
from utils.logger import Logger

# 設定ファイルのパスを定義
CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), "model_config.json")

def load_model_config():
    """モデル設定ファイルを読み込む"""
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # 設定ファイルが見つからない場合は空の辞書を返すか、エラーを出す
        # ここでは空の辞書を返し、後続の処理でデフォルトモデルを使うなどの対応をする
        return {}
    except json.JSONDecodeError:
        # JSONの形式が不正な場合も同様
        return {}

MODEL_CONFIGS = load_model_config()
DEFAULT_MODEL_NAME = "gemini-pro" # フォールバック用のデフォルトモデル名

class BaseVertexAI:
    def __init__(self, model_name: str = None):
        project_id = os.getenv("GCP_PROJECT")
        location = os.getenv("GCP_LOCATION", "us-central1")
        vertexai.init(project=project_id, location=location)
        self.logger = Logger(name=self.__class__.__name__).get_logger()

        if model_name:
            self.model_name = model_name
            self.logger.info(f"Using model_name from argument: {self.model_name}")
        else:
            class_name = self.__class__.__name__
            self.model_name = MODEL_CONFIGS.get(class_name, DEFAULT_MODEL_NAME)
            if class_name in MODEL_CONFIGS:
                self.logger.info(f"Loaded model_name from config for {class_name}: {self.model_name}")
            else:
                self.logger.warning(
                    f"No model_name found in config for {class_name}. "
                    f"Using default model: {DEFAULT_MODEL_NAME}"
                )

        self.response_scheme = None


    @property
    def model(self) -> GenerativeModel:
        return GenerativeModel(self.model_name)

    @property
    def generation_config(self):
        return GenerationConfig(
            response_mime_type="application/json",
            response_schema=self.response_scheme,
        )

    def invoke(self, contents):
        self.logger.info(f"contents > {contents[30:]}")
        response = self.model.generate_content(
            contents,
            generation_config=self.generation_config,
        )
        self.logger.info(f"response > {response}")
        return response
