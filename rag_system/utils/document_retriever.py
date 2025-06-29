# This file will contain dummy document retrieval functions.

def retrieve_work_reports(query: str, offset: int = 0, limit: int = 10) -> list[str]:
    """
    Retrieves dummy work reports.
    """
    print(f"DEBUG: Retrieving work reports for query='{query}', offset={offset}, limit={limit}")
    all_reports = [
        "作業レポート1: システムAのバグ修正を実施しました。",
        "作業レポート2: システムBのパフォーマンス改善を行いました。",
        "作業レポート3: 新機能Cの設計レビュー会議議事録。",
        "作業レポート4: インフラ障害Dの対応記録。",
        "作業レポート5: 定期メンテナンスEの結果報告。",
        "作業レポート6: ユーザーFからの問い合わせ対応ログ。",
        "作業レポート7: セキュリティパッチGの適用作業。",
        "作業レポート8: システムHの負荷テスト結果。",
        "作業レポート9: バージョンIへのアップグレード手順。",
        "作業レポート10: プロジェクトJの進捗報告。",
        "作業レポート11: システムKの設計変更提案。",
        "作業レポート12: データベースLのバックアップ確認。",
        "作業レポート13: ネットワークMの構成変更。",
        "作業レポート14: アプリケーションNのデプロイ作業。",
        "作業レポート15: 監視システムOのアラート対応。",
        "作業レポート16: 研修Pの参加報告。",
        "作業レポート17: コードレビューQのフィードバック。",
        "作業_レポート18: 定例会議Rの議事録。", # typo for testing
        "作業レポート19: 資料Sの作成と共有。",
        "作業レポート20: 緊急対応Tの事後報告。",
    ]
    return all_reports[offset:offset+limit]

def retrieve_manuals(query: str, offset: int = 0, limit: int = 10) -> list[str]:
    """
    Retrieves dummy manuals.
    """
    print(f"DEBUG: Retrieving manuals for query='{query}', offset={offset}, limit={limit}")
    all_manuals = [
        "手順書1: システムAの起動方法。",
        "手順書2: システムBのトラブルシューティングガイド。",
        "手順書3: 新機能Cの操作マニュアル。",
        "手順書4: インフラ障害D発生時の対応フロー。",
        "手順書5: 定期メンテナンスEの作業手順。",
        "手順書6: ユーザーF向けFAQ。",
        "手順書7: セキュリティパッチGの適用ガイドライン。",
        "手順書8: システムHのテスト手順書。",
        "手順書9: バージョンIへのアップグレードマニュアル。",
        "手順書10: プロジェクトJのコーディング規約。",
        "手順書11: システムKのAPI仕様書。",
        "手順書12: データベースLの運用マニュアル。",
        "手順書13: ネットワークMの設定手順。",
        "手順書14: アプリケーションNのリリース手順。",
        "手順書15: 監視システムOの導入手順。",
        "手順書16: 新人研修Pの教材。",
        "手順書17: コードレビューQのチェックリスト。",
        "手順書18: 会議Rの運営ルール。",
        "手順書19: ドキュメントSの書き方ガイド。",
        "手順書20: 緊急対応Tの連絡体制図。",
    ]
    return all_manuals[offset:offset+limit]
