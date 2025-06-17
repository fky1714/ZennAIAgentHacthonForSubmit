import time
from utils.logger import Logger

from agents import TaskSupporter, NotifyDesider

# ロガー初期化
logger = Logger(name="notify_service").get_logger()

last_notification_time = 0.0
quwiet_duration = 180

def can_notify_timing() -> bool:
    current_time = time.time()
    global last_notification_time
    return current_time - last_notification_time >= quwiet_duration

def generate_notification_message(encoded_frames, log_context="") -> str:
    """
    ユーザーをサポートするための通知メッセージを生成する。
    log_context: 過去のサポートログのコンテキスト
    """

    if not can_notify_timing():
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
            return ""
        else:
            if can_notify_timing():  # メッセージ生成時間中にすでに通知されている場合があるため、再確認
                global last_notification_time
                last_notification_time =  time.time()
                message = support_info.make_message()
                logger.info(f"message => {message}")
                return message
            else:
                return ""

    except Exception as e:
        log_context_snippet = f"{log_context[:50]}..." if log_context else "N/A"
        logger.error(
            "通知メッセージ生成中にエラーが発生しました: "
            f"len(frames)='{len(frames)}', "
            f"log_context='{log_context_snippet}', "
            f"error='{str(e)}'"
        )
        return ""
