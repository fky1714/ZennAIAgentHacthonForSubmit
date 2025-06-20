import os
import traceback # Ensure this import is present at the top of app.py
from dotenv import load_dotenv
import datetime
from datetime import timedelta # Ensure timedelta is imported
from google.cloud import storage
from flask import Flask, request, jsonify, session
import json
import uuid

from services import (
    upload_log_from_base64_screen_shot,
    make_report_by_log,
    make_procedure_from_mp4,
    generate_notification_message,
)

# Google認証用
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

# Loggerクラスのインポート
from utils.logger import Logger
from services.firestore_service import firestore_service


def check_and_generate_missing_reports(uid: str):
    logger.info(f"Starting check_and_generate_missing_reports for uid={uid}")
    try:
        today = datetime.datetime.now().date()

        # Get the most recent report to find the last log_date processed
        latest_reports = firestore_service.get_reports(uid=uid, page=1, page_size=1)

        last_processed_log_date = None
        if latest_reports and latest_reports[0].get("log_date"):
            try:
                last_processed_log_date = datetime.datetime.strptime(latest_reports[0]["log_date"], "%Y-%m-%d").date()
                logger.info(f"Last processed log_date for uid={uid} is {last_processed_log_date}")
            except ValueError:
                logger.warning(f"Could not parse log_date '{latest_reports[0]['log_date']}' for uid={uid}. Proceeding as if no last processed date.")
        else:
            logger.info(f"No recent reports with log_date found for uid={uid}. Will check from yesterday.")

        # Determine the start date for checking
        # If no last_processed_log_date, start from yesterday. Otherwise, start from the day after last_processed_log_date.
        current_check_date = last_processed_log_date + timedelta(days=1) if last_processed_log_date else today - timedelta(days=1)

        logger.info(f"Checking for missing reports for uid={uid} from {current_check_date} up to {today - timedelta(days=1)}")

        # Loop from start_date up to (but not including) today
        while current_check_date < today:
            date_str_to_check = current_check_date.strftime("%Y-%m-%d")
            logger.info(f"Processing date {date_str_to_check} for uid={uid}")

            try:
                # Check if a report for this log_date already exists
                existing_report = firestore_service.get_report_by_log_date(uid, date_str_to_check)
                if existing_report:
                    logger.info(f"Report for log_date {date_str_to_check} already exists for uid={uid}. Skipping.")
                    current_check_date += timedelta(days=1)
                    continue

                # If no report, check if logs exist for that day
                logger.info(f"No report found for {date_str_to_check}. Checking for logs for uid={uid}.")
                logs = firestore_service.download_log(uid, date=date_str_to_check)
                if not logs:
                    logger.info(f"No logs found for uid={uid} on {date_str_to_check}. Skipping report generation.")
                    current_check_date += timedelta(days=1)
                    continue

                logger.info(f"Logs found for uid={uid} on {date_str_to_check}. Attempting to generate report.")
                # If logs exist, generate the report
                report_content = make_report_by_log(uid, date_str_to_check)
                if report_content:
                    logger.info(f"Successfully generated report for uid={uid} for log_date {date_str_to_check}.")
                else:
                    # This case (logs exist but report_content is empty) might indicate an issue in make_report_by_log
                    # or it handled an edge case like "no tasks found in logs".
                    logger.info(f"make_report_by_log returned no content for uid={uid} for log_date {date_str_to_check}, though logs were present.")

            except Exception as e_inner:
                logger.error(f"Error processing date {date_str_to_check} for uid={uid}: {str(e_inner)}")
                # Optionally, log traceback: logger.error(traceback.format_exc())

            current_check_date += timedelta(days=1)

        logger.info(f"Finished check_and_generate_missing_reports for uid={uid}")

    except Exception as e_outer:
        logger.error(f"Outer error in check_and_generate_missing_reports for uid={uid}: {str(e_outer)}")
        # Optionally, log traceback: logger.error(traceback.format_exc())

app = Flask(__name__)
app.secret_key = "ThisIsHelloween"
logger = Logger(name="app").get_logger()

# Load environment variables from .env file
load_dotenv()

# Set Google Cloud credentials
env_gac = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if env_gac:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = env_gac
    logger.info(f"Using GOOGLE_APPLICATION_CREDENTIALS from .env: {env_gac}")
else:
    default_creds_path = "credentials.json"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = default_creds_path
    logger.info(
        f"GOOGLE_APPLICATION_CREDENTIALS not found in .env, using default: {default_creds_path}"
    )

storage_client = storage.Client()
BUCKET_NAME = os.getenv("BUCKET_NAME")


# ヘルパー関数: 実効UIDを取得
def get_effective_uid():
    """
    セッションから実効UIDを取得する。
    google_uidがあればそれを返し、なければsession_uuidを使う。
    どちらもなければ新しいsession_uuidを生成して返す。
    """
    if "google_uid" in session:
        logger.debug(f"Using google_uid: {session['google_uid']}")
        return session["google_uid"]
    elif "session_uuid" in session:
        logger.debug(f"Using session_uuid: {session['session_uuid']}")
        return session["session_uuid"]
    else:
        new_uuid = str(uuid.uuid4())
        session["session_uuid"] = new_uuid
        logger.info(f"Generated new session_uuid: {new_uuid}")
        return new_uuid


@app.route("/google_login", methods=["POST"])
def google_login():
    try:
        data = request.json
        logger.info(f"/google_login リクエスト受信: {data}")
        id_token_str = data.get("id_token")
        if not id_token_str:
            logger.warning("IDトークンがありません")
            return (
                jsonify({"status": "error", "message": "IDトークンがありません"}),
                400,
            )

        # GoogleのIDトークンを検証
        req = grequests.Request()
        idinfo = id_token.verify_oauth2_token(id_token_str, req)
        # idinfo['sub']がGoogleのUID
        uid = idinfo.get("sub")
        email = idinfo.get("email")
        session["google_uid"] = uid
        session["google_email"] = email

        logger.info(f"Googleログイン成功: uid={uid}, email={email}")
        return jsonify({"status": "success", "uid": uid, "email": email})

    except Exception as e:
        logger.error(f"Googleログイン失敗: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/record_frame", methods=["POST"])
def record_frame():
    try:
        uid = get_effective_uid()
        logger.info(f"/record_frame リクエスト受信: uid={uid}")

        data = request.json

        if "frames" in data and isinstance(data["frames"], list):
            base64_frames = data["frames"]
            user_request = data.get("user_request", "")
            wrapped_msg = (
                f"フレーム配列受信: {len(base64_frames)}枚, uid={uid}, "
                f"user_request='{user_request}'"
            )
            logger.info(wrapped_msg)
            upload_log_from_base64_screen_shot(uid, user_request, base64_frames)

        result = {"status": "success"}
        logger.info(f"フレーム記録成功: uid={uid}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"フレーム記録失敗: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/make_report", methods=["POST"])
def make_report():
    try:
        # セッションからUIDを参照可能
        uid = get_effective_uid()  # session.get("google_uid") から変更
        logger.info(f"/make_report リクエスト受信: uid={uid}")
        # 必要に応じてgoogle_uidを使って処理
        report = make_report_by_log(uid)
        result = {
            "status": "success",
            "report": report,
        }

        logger.info(f"レポート生成成功: uid={uid}")
        return json.dumps(result)

    except Exception as e:
        logger.error(f"レポート生成失敗: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/create_procedure", methods=["POST"])
def create_procedure():
    try:
        # セッションからUIDを参照可能
        uid = get_effective_uid()  # session.get("google_uid") から変更
        logger.info(f"/create_procedure リクエスト受信: uid={uid}")

        data = request.json
        procedure = ""
        task_name = data.get("task_name", "")
        video_url = data.get("video_url", "")
        user_request = data.get("user_request", "")  # Extract user_request
        logger.info(f"video_url: {video_url}")

        if video_url:
            procedure = make_procedure_from_mp4(
                uid,
                video_url,
                user_request,  # Pass user_request
                task_name,
            )
            logger.info(f"手順書作成成功: \n{procedure}")
            status = "success"

        else:
            logger.error("手順書作成失敗")
            status = "error"

        result = {
            "status": status,
            "procedure": procedure,  # 生の文字列
        }
        if status == "error" and not video_url:
            result["message"] = "No video_url provided to create procedure."

        return jsonify(result)  # Use jsonify for correct Content-Type header

    except Exception as e:
        logger.error(f"手順書作成失敗: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/check_login", methods=["GET"])
def check_login():
    uid = session.get("google_uid")
    email = session.get("google_email")

    if uid: # User is logged in or has an effective_uid via session
        try:
            today_str = datetime.datetime.now().strftime("%Y-%m-%d")
            last_check_date = firestore_service.get_last_auto_report_check_date(uid)

            if last_check_date != today_str:
                logger.info(f"Running automatic report check for uid={uid} for date={today_str}. Last check was on {last_check_date}.")
                # Call the function (assuming it's defined in app.py or imported)
                check_and_generate_missing_reports(uid)
                firestore_service.update_last_auto_report_check_date(uid, today_str)
                logger.info(f"Updated last_auto_report_check_date for uid={uid} to {today_str}.")
            else:
                logger.info(f"Automatic report check already performed today ({today_str}) for uid={uid}.")

        except Exception as e_auto_report:
            logger.error(f"Error during automatic report check for uid={uid}: {str(e_auto_report)}")
            # Do not let this break the /check_login functionality

    # Original /check_login response logic
    if uid and email:
        return jsonify({"status": "logged_in", "uid": uid, "email": email})
    else:
        # If not google_uid, try to get effective_uid to run the check for session-based users too
        # This part depends on whether non-Google logged-in users should also have this feature.
        # For now, let's stick to the original logic that it runs if 'uid' (which is google_uid here) is present.
        # If effective_uid should be used, the logic for getting uid at the start of this function needs adjustment.
        # The current problem description implies "user" in a general sense, but Firestore structure is users/{uid}/...
        # So it should align with the UID used for storing logs and reports.
        # `get_effective_uid()` could be called here if we want to run it for non-Google-logged-in users too.
        # For now, the current structure with `uid = session.get("google_uid")` is fine.
        return jsonify({"status": "not_logged_in"})


@app.route("/")
def index():
    logger.info("index.htmlリクエスト受信")
    return app.send_static_file("index.html")


# --- レポートAPI ---


# --- 手順書API ---
@app.route("/api/procedures", methods=["GET"])
def api_get_procedures():
    """
    手順書一覧取得API
    レポート一覧と同様に、ページングを受け取り手順書一覧を返却します。
    """
    # 実効UIDを取得する
    effective_uid = get_effective_uid()
    logger.info(f"GET /api/procedures called. effective_uid={effective_uid}")
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    page_size = int(request.args.get("page_size", 10))
    if page_size < 1:
        page_size = 10  # Default to 10 if invalid
    logger.info(
        logger.info(
            "Fetching procedures for user: %s page=%d, page_size=%d",
            effective_uid,
            page,
            page_size,
        )
    )
    procedures = firestore_service.get_procedures(
        effective_uid, page, page_size
    )  # このメソッドをfirestore_service側で定義
    logger.info(f"Returning {len(procedures)} procedures.")
    return jsonify({"status": "success", "procedures": procedures})


@app.route("/api/procedures/<procedure_id>", methods=["GET"])
def api_get_procedure(procedure_id):
    """
    個別手順書取得API
    """
    effective_uid = get_effective_uid()  # 実効UIDを取得
    wrapped_procedures_msg = (
        f"GET /api/procedures/<id> called. effective_uid={effective_uid}, "
        f"procedure_id={procedure_id}"
    )
    logger.info(wrapped_procedures_msg)
    procedure = firestore_service.get_procedure(
        effective_uid, procedure_id
    )  # このメソッドをfirestore_service側で定義
    if procedure:
        return jsonify({"status": "success", "procedure": procedure})
    else:
        return jsonify({"status": "error", "message": "Not found"}), 404


@app.route("/api/procedures/<procedure_id>", methods=["PUT"])
def api_update_procedure(procedure_id):
    effective_uid = get_effective_uid()
    logger.info(
        f"PUT /api/procedures/{procedure_id} called. effective_uid={effective_uid}"
    )
    try:
        data = request.json
        content = data.get("content", "")

        # Firestoreの手順書はtask_name=procedure_idで管理されている
        updated_procedure = firestore_service.update_procedure(effective_uid, procedure_id, content)

        if updated_procedure is None: # Or some other way to check if update failed in service layer
            logger.warning(f"Update procedure returned None for procedure_id: {procedure_id}, user: {effective_uid}")
            # Consider if firestore_service.update_procedure can return None for a "not found" or "failed update"
            # For now, let's assume it raises an exception on failure or returns the updated doc.
            # If it can return None for a failure that isn't an exception, that needs specific handling.

        logger.info(f"Procedure {procedure_id} updated successfully for user {effective_uid}.")
        return jsonify({"status": "success", "content": updated_procedure})

    except Exception as e:
        logger.error(f"Error in api_update_procedure for procedure_id {procedure_id}:")
        logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": "An unexpected error occurred on the server while updating the procedure.",
            "detail": str(e)
        }), 500


@app.route("/api/procedures/<procedure_id>", methods=["DELETE"])
def api_delete_procedure(procedure_id):
    """
    個別手順書削除API
    """
    effective_uid = get_effective_uid()
    logger.info(
        f"DELETE /api/procedures/<id> called. effective_uid={effective_uid}, procedure_id={procedure_id}"
    )
    uid = session.get("google_uid")
    if not uid:
        logger.warning("Not logged in (google_uid not found). Returning 401.")
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    try:
        if not hasattr(firestore_service, "delete_procedure"):
            logger.error(
                "Critical: firestore_service.delete_procedure method not found! This needs to be implemented."
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Server configuration error: delete_procedure service not implemented.",
                    }
                ),
                500,
            )

        success = firestore_service.delete_procedure(uid, procedure_id)

        if success:
            logger.info(
                f"Procedure '{procedure_id}' deleted successfully for user '{uid}'."
            )
            return (
                jsonify(
                    {"status": "success", "message": "Procedure deleted successfully"}
                ),
                200,
            )
        else:
            logger.warning(
                f"Procedure '{procedure_id}' not found or could not be deleted for user '{uid}'."
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Procedure not found or could not be deleted",
                    }
                ),
                404,
            )

    except Exception as e:
        logger.error(
            f"Error deleting procedure '{procedure_id}' for user '{uid}': {str(e)}"
        )
        import traceback

        logger.error(traceback.format_exc())
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "An internal server error occurred during deletion.",
                }
            ),
            500,
        )


@app.route("/api/reports", methods=["GET"])
def api_get_reports():
    effective_uid = get_effective_uid()  # 実効UIDを取得
    logger.info(f"GET /api/reports called. effective_uid={effective_uid}")
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    page_size = int(request.args.get("page_size", 10))
    if page_size < 1:
        page_size = 10  # Default to 10 if invalid
    logger.info(f"get_reports: uid={effective_uid} page={page} page_size={page_size}")
    reports = firestore_service.get_reports(effective_uid, page, page_size)
    return jsonify({"status": "success", "reports": reports})


@app.route("/api/reports/<report_id>", methods=["GET"])
def api_get_report(report_id):
    effective_uid = get_effective_uid()  # 実効UIDを取得
    wrapped_report_msg = (
        f"GET /api/reports/<id> called. effective_uid={effective_uid}, "
        f"report_id={report_id}"
    )
    logger.info(wrapped_report_msg)
    report = firestore_service.get_report(effective_uid, report_id)
    if report:
        return jsonify({"status": "success", "report": report})
    else:
        return jsonify({"status": "error", "message": "Not found"}), 404


@app.route("/api/reports", methods=["POST"])
def api_create_report():
    effective_uid = get_effective_uid()  # 実効UIDを取得
    logger.info(f"POST /api/reports called. effective_uid={effective_uid}")
    data = request.json
    title = data.get("title", "")
    content = data.get("content", "")
    date = data.get("date", "")
    report = firestore_service.create_report(effective_uid, title, content, date)
    return jsonify({"status": "success", "report": report})


@app.route("/api/reports/<report_id>", methods=["PUT"])
def api_update_report(report_id):
    effective_uid = get_effective_uid()  # 実効UIDを取得
    wrapped_put_report_msg = (
        f"PUT /api/reports/<id> called. effective_uid={effective_uid}, "
        f"report_id={report_id}"
    )
    logger.info(wrapped_put_report_msg)
    data = request.json
    title = data.get("title", "")
    content = data.get("content", "")
    report = firestore_service.update_report(effective_uid, report_id, title, content)
    return jsonify({"status": "success", "content": report})


@app.route("/api/reports/<report_id>", methods=["DELETE"])
def api_delete_report(report_id):
    effective_uid = get_effective_uid()  # 実効UIDを取得
    wrapped_delete_report_msg = (
        f"DELETE /api/reports/<id> called. effective_uid={effective_uid}, "
        f"report_id={report_id}"
    )
    logger.info(wrapped_delete_report_msg)
    firestore_service.delete_report(effective_uid, report_id)
    return jsonify({"status": "success"})


@app.route("/api/notify_support", methods=["POST"])
def notify_support():
    """
    呼び出され、送信されたフレームに基づいて必要があれば通知メッセージを返すAPI
    """
    try:
        uid = get_effective_uid()
        logger.info(f"POST /api/notify_support called by uid={uid}")

        # フレームデータをリクエストボディのJSONから取得
        frames = []
        log_context = ""  # Default value

        if request.json:
            frames = request.json.get("frames", [])
            log_context = request.json.get("log_context", "")  # Retrieve log_context

        if not frames:
            logger.info("No frames received in the request.")
            # フレームがなければ通知すべきメッセージもなし
            return jsonify({"status": "no_frames", "notification_message": ""})

        logger.info(
            f"Received {len(frames)} frames and log_context: '{log_context[:100]}...' for AI support."
        )  # Log context

        message = ""
        try:
            # Pass log_context to the service function
            message = generate_notification_message(frames, log_context)
        except Exception as e:
            logger.error(f"通知メッセージ生成失敗: {str(e)}")

        if message:
            return jsonify({"status": "success", "notification_message": message})
        else:
            return jsonify({"status": "no_support_needed", "notification_message": ""})

    except Exception as e:
        logger.error(f"/api/notify_support エラー: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/upload_video", methods=["POST"])
def upload_video():
    effective_uid = get_effective_uid()
    logger.info(f"POST /upload_video called by uid={effective_uid}")

    if "video_file" not in request.files:
        logger.warning("No video file part in the request.")
        return jsonify({"status": "error", "message": "No video file part"}), 400

    file = request.files["video_file"]

    if file.filename == "":
        logger.warning("No selected video file.")
        return jsonify({"status": "error", "message": "No selected file"}), 400

    if file:
        try:
            # Generate a unique filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            unique_id = uuid.uuid4().hex
            filename = f"{timestamp}_{unique_id}_{file.filename}"

            bucket = storage_client.bucket(BUCKET_NAME)
            blob = bucket.blob(filename)

            logger.info(f"Uploading video '{filename}' to GCS bucket '{BUCKET_NAME}'.")
            # Upload the file
            blob.upload_from_file(file.stream, content_type=file.content_type)

            blob.make_public()

            public_url = blob.public_url
            logger.info(
                f"Video '{filename}' uploaded successfully. Public URL: {public_url}"
            )

            return jsonify({"status": "success", "video_url": public_url}), 200

        except Exception as e:
            logger.error(f"Error uploading video to GCS: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return (
                jsonify(
                    {"status": "error", "message": f"Failed to upload video: {str(e)}"}
                ),
                500,
            )
    else:
        logger.warning("Video file not found or invalid.")
        return jsonify({"status": "error", "message": "Invalid file"}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Flaskアプリ起動 on port {port}")
    app.run(host="0.0.0.0", port=port)

# Removed duplicate block
