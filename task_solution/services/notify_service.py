import time
from utils.logger import Logger

from agents import TaskSupporter, NotifyDesider

# ロガー初期化
logger = Logger(name="notify_service").get_logger()

# Last notification time, initialized to 0.0 to allow immediate first notification
last_notification_time = 0.0


def generate_notification_message(encoded_frames, log_context="") -> str:
    """
    ユーザーをサポートするための通知メッセージを生成する。
    log_context: 過去のサポートログのコンテキスト
    """
    current_time = time.time()
    global last_notification_time

    # Check for cooldown
    if current_time - last_notification_time < 180:  # 3 minutes cooldown
        logger.info("Notification skipped due to 3-minute cooldown.")
        return ""

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
            if message:  # If a message was generated
                last_notification_time = current_time
            message = support_info.make_message()

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
