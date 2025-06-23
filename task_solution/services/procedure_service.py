from agents.procedure_descriptor import (
    VideoAnalyzer,
    ConfidentialInfoReplacer,
    ProcedureDescriptor,
)
from services.firestore_service import firestore_service
from utils.logger import Logger

logger = Logger(name="procedure_service").get_logger()


def make_procedure_from_mp4(
    uid: str, video_url: str, user_request: str, task_name: str = ""
):
    """
    base64エンコードされたスクリーンショット群から手順書を生成する
    - 3フレームごとに分割しscreen_analyzerで分析
    - 分析結果をまとめてログ化
    - ProcedureDescriptorで手順書体裁に
    - Firestoreに保存
    """
    logger.info(f"uid: {uid}, task_name: {task_name}, user_request: '{user_request}'")

    # 動画から作業に関する情報wを抽出する
    va = VideoAnalyzer()
    procedure_info_text: str = va.analyze_video(
        task_name=task_name, video_uri=video_url, user_query=user_request
    )

    # 機密情報を変数化する
    cir = ConfidentialInfoReplacer()
    procedure_info_text = cir.replace(procedure_info_text=procedure_info_text)

    # ProcedureDescriptorで手順書体裁に
    pd = ProcedureDescriptor()
    procedure_info = pd.extract_procedure_info(procedure_info_text=procedure_info_text)

    procedure_doc = procedure_info.to_document()
    logger.info(f"procedure_doc: {procedure_doc}")

    firestore_service.create_procedure(uid, task_name, procedure_doc)
    return procedure_doc
