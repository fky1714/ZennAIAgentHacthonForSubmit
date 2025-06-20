from google.cloud import firestore
from datetime import datetime

from utils.logger import Logger


logger = Logger(name="firestore_service").get_logger()


class FirestoreService:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super(FirestoreService, cls).__new__(cls)
            cls.__instance.db = firestore.Client()
            cls.__instance.today_str = datetime.now().strftime("%Y-%m-%d")
        return cls.__instance

    def upload_log(self, uid: str, log_data: str):
        """
        ログを users/{uid}/logs/{date} ドキュメントの logs 配列に追加
        """
        logger.info(f"upload_log: uid={uid} log_data={log_data}")

        today_str = datetime.now().strftime("%Y-%m-%d")
        doc_ref = (
            self.db.collection("users")
            .document(uid)
            .collection("logs")
            .document(today_str)
        )
        doc = doc_ref.get()
        if doc.exists:
            logs = doc.to_dict().get("logs", [])
            logs.append(log_data)
            doc_ref.update({"logs": logs, "updated_at": datetime.now()})
        else:
            doc_ref.set(
                {
                    "logs": [log_data],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now(),
                }
            )

    def download_log(self, uid: str, date: str = None) -> str:
        """
        ログを users/{uid}/logs/{date} から取得
        """
        logger.info(f"download_log: uid={uid} date={date}")
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        doc_ref = (
            self.db.collection("users").document(uid).collection("logs").document(date)
        )
        doc = doc_ref.get()
        if doc.exists:
            logs = doc.to_dict().get("logs", [])
            logs = [log.replace("\n", " ") for log in logs]
            log_text = "\n".join(logs)
            return log_text
        else:
            return ""

    # --- レポートCRUD機能追加 ---
    def get_reports(self, uid: str, page: int = 1, page_size: int = 10):
        logger.info("get_reports: uid=%s page=%s page_size=%s", uid, page, page_size)
        reports_collection = (
            self.db.collection("users").document(uid).collection("reports")
        )

        query = reports_collection.order_by(
            "created_at", direction=firestore.Query.DESCENDING
        )

        # Calculate offset
        offset_val = (page - 1) * page_size

        paginated_query = query.limit(page_size).offset(offset_val)
        docs_snapshot = paginated_query.stream()

        results = []
        for d in docs_snapshot: # Iterate over the result of the paginated query
            dat = d.to_dict()
            dat["id"] = d.id
            results.append(dat)
        return results

    def get_report(self, uid: str, report_id: str):
        """レポート詳細取得"""
        logger.info(f"get_report: uid={uid}, report_id={report_id}")

        doc_ref = (
            self.db.collection("users")
            .document(uid)
            .collection("reports")
            .document(report_id)
        )
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["id"] = doc.id
            return data
        return None

    def create_report(self, uid: str, title: str, content: str, log_date: str = None):
        """レポート新規作成"""
        if log_date:
            logger.info(f"create_report: uid={uid} title={title} log_date={log_date}")
        else:
            logger.info(f"create_report: uid={uid} title={title}")

        users_doc = self.db.collection("users").document(uid)
        reports_ref = users_doc.collection("reports")
        new_doc = reports_ref.document()
        now = datetime.now()
        report_data = {
            "title": title,
            "content": content,
            "created_at": now,
            "updated_at": now,
        }
        if log_date:
            report_data["log_date"] = log_date
        new_doc.set(report_data)
        data = new_doc.get().to_dict()
        data["id"] = new_doc.id
        return data

    def get_report_by_log_date(self, uid: str, log_date: str) -> dict | None:
        '''Checks if a report exists for a specific log_date.'''
        logger.info(f"get_report_by_log_date: uid={uid}, log_date={log_date}")
        reports_ref = self.db.collection("users").document(uid).collection("reports")
        query = reports_ref.where("log_date", "==", log_date).limit(1)
        docs = query.stream()
        for doc in docs: # Should be at most one due to limit(1)
            if doc.exists:
                report_data = doc.to_dict()
                report_data["id"] = doc.id
                logger.info(f"Found report for log_date {log_date}: id={doc.id}")
                return report_data
        logger.info(f"No report found for log_date {log_date}")
        return None

    def update_report(self, uid: str, report_id: str, title: str, content: str):
        """レポート更新"""
        logger.info("update_report: uid=%s, report_id=%s", uid, report_id)

        doc_ref = (
            self.db.collection("users")
            .document(uid)
            .collection("reports")
            .document(report_id)
        )
        now = datetime.now()
        doc_ref.update({"title": title, "content": content, "updated_at": now})
        data = doc_ref.get().to_dict()
        data["id"] = report_id
        return data

    def delete_report(self, uid: str, report_id: str):
        """レポート削除"""
        logger.info(f"delete_report: uid={uid}, report_id={report_id}")

        doc_ref = (
            self.db.collection("users")
            .document(uid)
            .collection("reports")
            .document(report_id)
        )
        doc_ref.delete()
        return True

    def get_procedures(self, uid: str, page: int = 1, page_size: int = 10):
        """手順一覧をタスク名の昇順でページング取得"""
        logger.info("get_procedures: uid=%s page=%s page_size=%s", uid, page, page_size)

        procedures_collection = (
            self.db.collection("users").document(uid).collection("procedures")
        )

        query = procedures_collection.order_by(
            "created_at", direction=firestore.Query.ASCENDING
        )

        # Calculate offset
        offset_val = (page - 1) * page_size

        paginated_query = query.limit(page_size).offset(offset_val)
        docs_snapshot = paginated_query.stream()

        results = []
        for doc_snap in docs_snapshot: # Iterate over the result of the paginated query
            data = doc_snap.to_dict()
            data["task_name"] = doc_snap.id
            results.append(data)

        return results

    def get_procedure(self, uid: str, task_name: str):
        """手順詳細取得"""
        logger.info(f"get_procedure: uid={uid}, task_name={task_name}")

        doc_ref = (
            self.db.collection("users")
            .document(uid)
            .collection("procedures")
            .document(task_name)
        )
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data["task_name"] = task_name
            return data
        return None

    def create_procedure(self, uid: str, task_name: str, procedure_data: str):
        """手順新規作成"""
        logger.info(f"create_procedure: uid={uid}, task_name={task_name}")
        doc_ref = (
            self.db.collection("users")
            .document(uid)
            .collection("procedures")
            .document(task_name)
        )
        now = datetime.now()
        doc_ref.set(
            {
                "content": procedure_data,
                "created_at": now,
                "updated_at": now,
            }
        )
        data = doc_ref.get().to_dict()
        data["task_name"] = task_name
        return data

    def update_procedure(self, uid: str, task_name: str, procedure_data: str):
        """手順更新"""
        logger.info(f"update_procedure: uid={uid}, task_name={task_name}")

        doc_ref = (
            self.db.collection("users")
            .document(uid)
            .collection("procedures")
            .document(task_name)
        )
        now = datetime.now()
        doc_ref.update({"content": procedure_data, "updated_at": now})
        data = doc_ref.get().to_dict()
        data["task_name"] = task_name
        return data

    def delete_procedure(self, uid: str, task_name: str):
        """手順削除"""
        logger.info(f"delete_procedure: uid={uid}, task_name={task_name}")

        doc_ref = (
            self.db.collection("users")
            .document(uid)
            .collection("procedures")
            .document(task_name)
        )
        doc_ref.delete()
        return True

    def get_last_auto_report_check_date(self, uid: str) -> str | None:
        '''Retrieves the last date the automatic report check was performed for a user.'''
        logger.info(f"get_last_auto_report_check_date: uid={uid}")
        try:
            doc_ref = self.db.collection("users").document(uid).collection("metadata").document("auto_report_tracker")
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict().get("last_check_date")
            return None
        except Exception as e:
            logger.error(f"Error getting last_auto_report_check_date for uid={uid}: {str(e)}")
            return None # Or re-raise if critical

    def update_last_auto_report_check_date(self, uid: str, date_str: str):
        '''Updates the last date the automatic report check was performed.'''
        logger.info(f"update_last_auto_report_check_date: uid={uid}, date_str={date_str}")
        try:
            doc_ref = self.db.collection("users").document(uid).collection("metadata").document("auto_report_tracker")
            doc_ref.set({"last_check_date": date_str, "updated_at": datetime.now()}, merge=True)
        except Exception as e:
            logger.error(f"Error updating last_auto_report_check_date for uid={uid}: {str(e)}")
            # Or re-raise if critical


firestore_service = FirestoreService()
