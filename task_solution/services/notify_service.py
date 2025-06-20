import time
from utils.logger import Logger

from agents import TaskSupporter, NotifyDesider

# ロガー初期化
logger = Logger(name="notify_service").get_logger()


def generate_notification_message(encoded_frames, log_context="") -> str:
    """
    ユーザーをサポートするための通知メッセージを生成する。
    log_context: 過去のサポートログのコンテキスト
    """
    start_time = time.time()
    try:
        frames = [frame.split(",")[1] for frame in encoded_frames if "," in frame]

        ts = TaskSupporter()
        support_info = ts.get_support(
            encoded_frames=frames,
        )

        nd = NotifyDesider()
        notify_log_string = log_context.split("\n")[0]
        if not nd.is_need_notify(
            support_info=support_info, log_context=notify_log_string
        ):
            message = ""
        else:
            message = support_info.make_message()

        end_time = time.time()
        logger.info(
            "generate_notification_message execution time: "
            f"{end_time - start_time} seconds"
        )
        return message
    except Exception as e:
        end_time = time.time()
        logger.info(
            "generate_notification_message execution time (error): "
            f"{end_time - start_time} seconds"
        )
        log_context_snippet = f"{log_context[:50]}..." if log_context else "N/A"
        logger.error(
            "通知メッセージ生成中にエラーが発生しました: "
            f"len(frames)='{len(frames)}', "
            f"log_context='{log_context_snippet}', "
            f"error='{str(e)}'"
        )
        return ""
