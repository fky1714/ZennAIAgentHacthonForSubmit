# This file will contain document retrieval functions.
# It will be modified to use FirestoreService.

# まずは必要なモジュールをインポート
import sys
import os

# プロジェクトルートをPythonパスに追加 (直接実行時やテスト用)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from task_solution.services.firestore_service import firestore_service
except ImportError:
    # CI環境など、task_solution が直接パスに含まれない場合を考慮 (ローカル実行時は上記で解決されるはず)
    # もし PYTHONPATH が適切に設定されていればここは通らない
    print("DEBUG: task_solution.services.firestore_service のインポートに失敗。ダミーモードで動作します。")
    firestore_service = None


def _format_report_doc(doc: dict) -> str:
    """Firestoreから取得したレポートドキュメントを文字列にフォーマットする"""
    title = doc.get('title', 'タイトルなし')
    content = doc.get('content', '内容なし')
    # created_at = doc.get('created_at', '') # 必要であれば日付情報も追加
    # updated_at = doc.get('updated_at', '')
    # return f"作業レポート ID: {doc.get('id', '不明')}\nタイトル: {title}\n内容:\n{content}"
    # より自然なRAG向けテキストとして、タイトルと内容を主体にする
    return f"作業レポート「{title}」:\n{content}"

def _format_manual_doc(doc: dict) -> str:
    """Firestoreから取得した手順書ドキュメントを文字列にフォーマットする"""
    task_name = doc.get('task_name', 'タスク名なし')
    content = doc.get('content', '内容なし')
    # created_at = doc.get('created_at', '')
    # updated_at = doc.get('updated_at', '')
    # return f"作業手順書 タスク名: {task_name}\n内容:\n{content}"
    return f"作業手順書「{task_name}」:\n{content}"


def retrieve_work_reports(user_query: str, uid: str, offset: int = 0, limit: int = 10) -> list[str]:
    """
    Retrieves work reports from Firestore for a given user.
    Args:
        user_query: The user's query (currently unused for retrieval, but kept for interface consistency).
        uid: The user ID for whom to retrieve reports.
        offset: The starting point for pagination. Firestore's get_reports uses page number.
        limit: The maximum number of reports to retrieve.
    Returns:
        A list of strings, where each string is a formatted work report.
    """
    print(f"DEBUG: Retrieving work reports from Firestore for uid='{uid}', query='{user_query}', offset={offset}, limit={limit}")
    if not firestore_service:
        print("DEBUG: Firestore service not available. Returning dummy work reports.")
        # ダミーデータ (firestore_service が利用できない場合のフォールバック)
        all_reports = [
            "ダミー作業レポート1: システムAのバグ修正を実施しました。",
            "ダミー作業レポート2: システムBのパフォーマンス改善を行いました。",
        ] * 10 # 十分な量を確保
        return all_reports[offset:offset+limit]

    try:
        # FirestoreServiceのget_reportsは1ベースのページ番号を使用
        page = (offset // limit) + 1
        reports_data = firestore_service.get_reports(uid=uid, page=page, page_size=limit)

        formatted_reports = [_format_report_doc(doc) for doc in reports_data]

        print(f"DEBUG: Retrieved {len(formatted_reports)} work reports from Firestore.")
        return formatted_reports
    except Exception as e:
        print(f"ERROR: Failed to retrieve work reports from Firestore: {e}")
        return []

def retrieve_manuals(user_query: str, uid: str, offset: int = 0, limit: int = 10) -> list[str]:
    """
    Retrieves manuals (procedures) from Firestore for a given user.
    Args:
        user_query: The user's query (currently unused for retrieval).
        uid: The user ID for whom to retrieve manuals.
        offset: The starting point for pagination. Firestore's get_procedures uses page number.
        limit: The maximum number of manuals to retrieve.
    Returns:
        A list of strings, where each string is a formatted manual.
    """
    print(f"DEBUG: Retrieving manuals from Firestore for uid='{uid}', query='{user_query}', offset={offset}, limit={limit}")
    if not firestore_service:
        print("DEBUG: Firestore service not available. Returning dummy manuals.")
        # ダミーデータ
        all_manuals = [
            "ダミー手順書1: システムAの起動方法。",
            "ダミー手順書2: システムBのトラブルシューティングガイド。",
        ] * 10
        return all_manuals[offset:offset+limit]

    try:
        # FirestoreServiceのget_proceduresは1ベースのページ番号を使用
        page = (offset // limit) + 1
        manuals_data = firestore_service.get_procedures(uid=uid, page=page, page_size=limit)

        formatted_manuals = [_format_manual_doc(doc) for doc in manuals_data]

        print(f"DEBUG: Retrieved {len(formatted_manuals)} manuals from Firestore.")
        return formatted_manuals
    except Exception as e:
        print(f"ERROR: Failed to retrieve manuals from Firestore: {e}")
        return []

if __name__ == '__main__':
    # FirestoreServiceが利用可能かどうかの確認
    if not firestore_service:
        print(" Firestore_service is not available. Skipping live tests.")
        print(" Please ensure Firestore emulator is running and GOOGLE_APPLICATION_CREDENTIALS is set,")
        print(" or that the application is running in an environment with Firestore access.")
    else:
        print("Firestore_service is available. Running live tests (requires Firestore emulator or live connection).")
        # テスト用のUID (実際の環境に合わせて変更またはモックする)
        # Firestoreエミュレータを使用している場合、このUIDでデータを作成しておく必要があります。
        test_uid = "test-user-123"
        print(f"--- Testing with UID: {test_uid} ---")

        print("\n--- Retrieving Work Reports ---")
        # ダミーデータがFirestoreにあれば取得できるはず
        # 事前にFirestoreエミュレータに test_uid でレポートデータを登録しておく
        # 例:
        # firestore_service.create_report(test_uid, "初回テストレポート", "これはFirestoreからの最初のテストレポートです。")
        # firestore_service.create_report(test_uid, "2番目のレポート", "これは2番目の作業報告です。色々やりました。")
        # for i in range(3, 15):
        #     firestore_service.create_report(test_uid, f"自動生成レポート{i}", f"レポート{i}の本文です。")

        reports = retrieve_work_reports("some query", uid=test_uid, offset=0, limit=5)
        if reports:
            for i, report in enumerate(reports):
                print(f"Report {i+1}:\n{report}\n---")
        else:
            print("No work reports retrieved. Ensure data exists in Firestore for the test UID or check Firestore connection.")

        print("\n--- Retrieving Manuals (Procedures) ---")
        # ダミーデータがFirestoreにあれば取得できるはず
        # 事前にFirestoreエミュレータに test_uid で手順書データを登録しておく
        # 例:
        # firestore_service.create_procedure(test_uid, "テスト手順書1", "これがFirestoreからの最初のテスト手順書です。")
        # firestore_service.create_procedure(test_uid, "テスト手順書2", "これが2番目の手順書。手順はA、B、C。")
        # for i in range(3, 15):
        #     firestore_service.create_procedure(test_uid, f"自動生成手順{i}", f"手順{i}の内容です。")

        manuals = retrieve_manuals("another query", uid=test_uid, offset=0, limit=5)
        if manuals:
            for i, manual in enumerate(manuals):
                print(f"Manual {i+1}:\n{manual}\n---")
        else:
            print("No manuals retrieved. Ensure data exists in Firestore for the test UID or check Firestore connection.")

        # オフセットのテスト
        print("\n--- Retrieving Work Reports with Offset ---")
        reports_offset = retrieve_work_reports("offset query", uid=test_uid, offset=5, limit=5)
        if reports_offset:
            for i, report in enumerate(reports_offset):
                print(f"Report (offset) {i+1}:\n{report}\n---")
        else:
            print("No work reports retrieved with offset.")

        # uid が存在しない場合のテストはFirestoreService側でエラーにならないのでここでは省略
        # (空リストが返るはず)
        print("\n--- Testing with non-existent UID ---")
        non_existent_uid = "does-not-exist-uid"
        reports_non_existent = retrieve_work_reports("query", uid=non_existent_uid, limit=2)
        if not reports_non_existent:
            print(f"Correctly_retrieved_no_reports for UID: {non_existent_uid}")
        else:
            print(f"ERROR: Retrieved reports for non-existent UID: {non_existent_uid}")

        manuals_non_existent = retrieve_manuals("query", uid=non_existent_uid, limit=2)
        if not manuals_non_existent:
            print(f"Correctly_retrieved_no_manuals for UID: {non_existent_uid}")
        else:
            print(f"ERROR: Retrieved manuals for non-existent UID: {non_existent_uid}")
