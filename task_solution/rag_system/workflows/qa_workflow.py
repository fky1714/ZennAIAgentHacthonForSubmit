import sys
import os

# プロジェクトルートをPythonパスに追加 (直接実行時用)
# 通常は呼び出し元でPYTHONPATHが設定されていることを期待
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.append(project_root)

from rag_system.agents.information_type_agent import InformationTypeAgent
from rag_system.agents.answer_generation_agent import AnswerGenerationAgent
from agents.vertex_ai.chatbot_agent import ChatbotAgent  # ChatbotAgent をインポート
from rag_system.utils.document_retriever import retrieve_work_reports, retrieve_manuals

# 回答に「情報なし」と判定するキーワード（実際のLLMの出力に応じて調整）
# このキーワードは AnswerGenerationAgent 側での判定に使われるため、QAWorkflowからは削除しても良い
NO_INFO_KEYWORDS = [
    "見つかりませんでした",
    "該当する情報はありません",
    "分かりません",
    "情報がありません",
]


class QAWorkflow:
    def __init__(self): # project と location の引数を削除
        self.info_type_agent = InformationTypeAgent()
        self.answer_gen_agent = AnswerGenerationAgent()
        self.chatbot_agent = ChatbotAgent()
        self.max_retries = 1  # 追加検索は1回まで (合計20件)

    def _determine_information_type(self, user_question: str) -> str:
        print(f"\nWORKFLOW: 情報種別を判断中...\n質問: {user_question}")
        info_type = self.info_type_agent.predict(user_question)
        print(f"WORKFLOW: 判断された情報種別: {info_type}")
        return info_type

    def _retrieve_documents(
        self,
        information_type: str,
        user_question: str,
        uid: str,
        offset: int = 0,
        limit: int = 10,
    ) -> list[str]:
        print(
            f"WORKFLOW: ドキュメントを取得中... UID: {uid}, タイプ: {information_type}, オフセット: {offset}, リミット: {limit}"
        )
        documents = []
        if information_type == "作業レポート":
            documents = retrieve_work_reports(
                user_query=user_question, uid=uid, offset=offset, limit=limit
            )
        elif information_type == "作業手順書":
            documents = retrieve_manuals(
                user_query=user_question, uid=uid, offset=offset, limit=limit
            )

        if documents:
            print(f"WORKFLOW: {len(documents)}件のドキュメントを取得しました。")
        else:
            print("WORKFLOW: ドキュメントは見つかりませんでした。")
        return documents

    def _generate_rag_answer(self, user_question: str, documents: list[str]) -> str:
        print("WORKFLOW: RAG回答を生成中...")
        answer = self.answer_gen_agent.predict(user_question, documents)
        print(f"WORKFLOW: 生成されたRAG回答: {answer}")
        return answer

    def _generate_general_answer(self, user_question: str) -> str:
        print("WORKFLOW: 一般知識の回答を生成中...")
        answer = self.chatbot_agent.generate_response(user_question)
        print(f"WORKFLOW: 生成された一般知識回答: {answer}")
        return answer

    def run(self, user_question: str, uid: str) -> str:  # uid 引数を追加
        print(
            f'\n====================\nWORKFLOW: Q&A処理開始\nユーザーの質問: "{user_question}", UID: {uid}\n===================='
        )

        information_type = self._determine_information_type(user_question)

        if information_type == "一般知識":
            print(
                "WORKFLOW: 一般知識に関する質問と判断。ChatbotAgent を使用します。"
            )
            final_answer = self._generate_general_answer(user_question)
            # 一般知識の場合、NO_INFO_KEYWORDS によるチェックは ChatbotAgent の応答の性質と合わないため削除
            print(f"WORKFLOW: 最終回答 (一般知識): {final_answer}")
            return final_answer

        documents = []
        final_answer = ""

        # 初回検索
        current_documents = self._retrieve_documents(
            information_type, user_question, uid=uid, offset=0, limit=10
        )
        documents.extend(current_documents)

        if not documents:
            # ドキュメントが見つからない場合は、その旨を伝える固定メッセージ
            final_answer = "関連する情報が見つかりませんでした。"
            print(f"WORKFLOW: 最終回答 (ドキュメントなし): {final_answer}")
            return final_answer

        final_answer = self._generate_rag_answer(user_question, documents)

        retries = 0
        # AnswerGenerationAgent が「情報なし」系のキーワードを返した場合に追加検索
        # NO_INFO_KEYWORDS は AnswerGenerationAgent の応答を想定して使用
        while (
            any(keyword in final_answer for keyword in NO_INFO_KEYWORDS)
            and retries < self.max_retries
        ):
            retries += 1
            print(
                f"WORKFLOW: 回答に十分な情報がないと判断。追加のドキュメントを検索します。(試行 {retries}/{self.max_retries})"
            )

            offset = retries * 10
            additional_documents = self._retrieve_documents(
                information_type, user_question, uid=uid, offset=offset, limit=10
            )

            if not additional_documents:
                print("WORKFLOW: 追加のドキュメントは見つかりませんでした。")
                break

            documents.extend(additional_documents)
            print(
                f"WORKFLOW: 合計{len(documents)}件のドキュメントで再度回答を生成します。"
            )
            final_answer = self._generate_rag_answer(user_question, documents)

        # RAGの最終回答ログを修正
        print(f"WORKFLOW: 最終回答 (RAG): {final_answer}")
        return final_answer


if __name__ == "__main__":
    # 簡単なテスト実行
    # GCPプロジェクトIDとロケーションを環境変数や設定ファイルから読み込むのが望ましい
    workflow = QAWorkflow(project="your-gcp-project", location="us-central1")

    # テストケース1: 作業レポートに関する質問 (初回で見つかる想定)
    q1 = "システムAのバグ修正はいつ完了しましたか？"
    # document_retriever.py の retrieve_work_reports のダミーデータに "作業レポート1: システムAのバグ修正を実施しました。" がある
    # AnswerGenerationAgent のダミー predict は具体的な日付までは返さないが、情報がある旨は返すはず
    test_uid = "test-user-for-qa-workflow"  # テスト用UID
    workflow.run(q1, uid=test_uid)

    # テストケース2: 作業手順書に関する質問 (追加検索が必要になるかもしれないケース)
    # document_retriever.py の retrieve_manuals のダミーデータに "手順書12: データベースLの運用マニュアル。" がある
    # AnswerGenerationAgent のダミー predict が「情報なし」と返した場合に追加検索する
    q2 = "データベースLの運用方法を教えて。"
    workflow.run(q2, uid=test_uid)

    # テストケース3: 一般知識に関する質問
    q3 = "日本の首都はどこですか？"
    workflow.run(q3, uid=test_uid)  # uidは渡されるが一般知識の場合は使われない

    # テストケース4: 情報が見つからない質問 (作業レポート)
    # 存在しないレポートを要求
    q4 = "存在しないプロジェクトXYZの進捗レポートは？"
    workflow.run(q4, uid=test_uid)

    # テストケース5: 情報種別は判断できるが、ドキュメントがないケース (作業手順書)
    # 10件取得しても該当なし、追加の10件でも該当なし
    q5 = "火星でのピザの作り方手順書"
    workflow.run(q5, uid=test_uid)
