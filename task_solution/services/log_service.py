from datetime import datetime

from agents import ScreenAnalyzer
from agents.report_maker import (
    ReportMaker,
    TaskTypeExtractor,
    TimeTableMaker,
)
from services.firestore_service import firestore_service
from utils.logger import Logger


logger = Logger(name="log_service").get_logger()


def upload_log_from_base64_screen_shot(
    uid: str, user_query: str, encoded_frames: list[str]
):
    try:
        frames = [frame.split(",")[1] for frame in encoded_frames if "," in frame]

        screen_analyzer = ScreenAnalyzer()
        output = screen_analyzer.analysis(frames, user_query=user_query)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record_string = f"{timestamp}: {output}"

        # Firestoreにログを保存
        firestore_service.upload_log(uid, record_string)
    except Exception as e:
        logger.error(f"Error uploading log for uid={uid}: {e}")
        raise e


def make_report_by_log(uid: str, log_date_str: str = None) -> str:
    """
    指定日付のログをまとめてLLMで作業レポートを生成する
    :param uid: ユーザーID
    :param log_date_str: "YYYY-MM-DD"形式の日付。指定がない場合は今日の日付
    :return: レポート文字列
    """
    target_date_str = log_date_str
    if target_date_str is None:
        target_date_str = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"make_report_by_log: uid={uid} for log_date={target_date_str}")

    log_text = firestore_service.download_log(uid, date=target_date_str)
    if not log_text:
        logger.info(f"No logs found for uid={uid} on date={target_date_str}. Skipping report generation.")
        return ""

    log_text_short = log_text[:30].replace("\n", " ")
    logger.info(f"make_report_by_log: uid={uid} log_text={log_text_short} for log_date={target_date_str}")

    report_maker = ReportMaker()
    task_type_extractor = TaskTypeExtractor()
    time_table_maker = TimeTableMaker()

    task_types = task_type_extractor.extract_task_type(log_text)

    time_table_list = time_table_maker.make_time_table(log_text, task_types.to_str())
    logger.info(f"Time table created for {target_date_str}: {time_table_list.to_str()}")

    report_info = report_maker.make_report(log_text)
    mark_down_report = report_info.to_markdown(time_table_list=time_table_list)
    logger.info(f"Report info for {target_date_str}: {report_info}")

    firestore_service.create_report(
        uid,
        title=report_info.title,
        content=mark_down_report,
        log_date=target_date_str
    )

    mark_down_report_short = mark_down_report[:50].replace("\n", " ")
    logger.info(f"=> {mark_down_report_short}")
    return mark_down_report
