from agents import ProcedureDescriptor
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

    # ProcedureDescriptorで手順書体裁に
    procedure_descriptor = ProcedureDescriptor()
    procedure_info = procedure_descriptor.analyze_video(
        task_name=task_name,
        video_uri=video_url,
        user_query=user_request,
    )

    procedure_doc = procedure_info.to_document()
    logger.info(f"procedure_doc: {procedure_doc}")

    firestore_service.create_procedure(uid, task_name, procedure_doc)
    return procedure_doc
