from google.cloud import firestore
from typing import List, Dict, Any, Optional
import re

from utils.logger import Logger

class FirestoreRepository:
    """Firestoreとのデータアクセスを担当"""
    
    def __init__(self):
        self.db = firestore.Client()
        self.logger = Logger(name=self.__class__.__name__)
    
    def get_user_reports(self, uid: str) -> List[Dict[str, Any]]:
        """ユーザーのレポート一覧を取得"""
        reports_ref = self.db.collection("users").document(uid).collection("reports")
        return [{"id": doc.id, **doc.to_dict()} for doc in reports_ref.stream()]
    
    def get_user_procedures(self, uid: str) -> List[Dict[str, Any]]:
        """ユーザーの手順一覧を取得"""
        procedures_ref = self.db.collection("users").document(uid).collection("procedures")
        return [{"id": doc.id, **doc.to_dict()} for doc in procedures_ref.stream()]
    
    def save_entity(self, uid: str, entity: Dict[str, Any]):
        """エンティティを保存"""
        entities_ref = self.db.collection("users").document(uid).collection("entities")
        doc_id = self._sanitize_doc_id(entity["name"])
        entities_ref.document(doc_id).set(entity, merge=True)
    
    def get_entity(self, uid: str, entity_name: str) -> Optional[Dict[str, Any]]:
        """エンティティを取得"""
        entities_ref = self.db.collection("users").document(uid).collection("entities")
        doc_id = self._sanitize_doc_id(entity_name)
        doc = entities_ref.document(doc_id).get()
        return doc.to_dict() if doc.exists else None
    
    def save_relation(self, uid: str, relation: Dict[str, Any], relation_id: str):
        """関係を保存"""
        relations_ref = self.db.collection("users").document(uid).collection("relations")
        relations_ref.document(relation_id).set(relation, merge=True)
    
    def get_relation(self, uid: str, relation_id: str) -> Optional[Dict[str, Any]]:
        """関係を取得"""
        relations_ref = self.db.collection("users").document(uid).collection("relations")
        doc = relations_ref.document(relation_id).get()
        return doc.to_dict() if doc.exists else None
    
    def save_knowledge_node(self, uid: str, node: Dict[str, Any], node_id: str):
        """ナレッジノードを保存"""
        nodes_ref = self.db.collection("users").document(uid).collection("knowledge_nodes")
        nodes_ref.document(node_id).set(node, merge=True)
    
    def search_entities_by_keyword(self, uid: str, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        """キーワードでエンティティを検索"""
        entities_ref = self.db.collection("users").document(uid).collection("entities")
        query = entities_ref.where("name", ">=", keyword.lower()).where("name", "<=", keyword.lower() + "\uf8ff").limit(limit)
        return [doc.to_dict() for doc in query.stream()]
    
    def get_all_relations(self, uid: str) -> List[Dict[str, Any]]:
        """全ての関係を取得"""
        relations_ref = self.db.collection("users").document(uid).collection("relations")
        return [doc.to_dict() for doc in relations_ref.stream()]
    
    def get_knowledge_node(self, uid: str, node_id: str) -> Optional[Dict[str, Any]]:
        """ナレッジノードを取得"""
        nodes_ref = self.db.collection("users").document(uid).collection("knowledge_nodes")
        doc = nodes_ref.document(node_id).get()
        return doc.to_dict() if doc.exists else None
    
    def clear_collection(self, uid: str, collection_name: str):
        """コレクションをクリア"""
        collection_ref = self.db.collection("users").document(uid).collection(collection_name)
        docs = collection_ref.stream()
        
        batch = self.db.batch()
        count = 0
        for doc in docs:
            batch.delete(doc.reference)
            count += 1
            if count >= 500:
                batch.commit()
                batch = self.db.batch()
                count = 0
        
        if count > 0:
            batch.commit()
    
    def get_collection_count(self, uid: str, collection_name: str) -> int:
        """コレクションのドキュメント数を取得"""
        collection_ref = self.db.collection("users").document(uid).collection(collection_name)
        return len(list(collection_ref.stream()))
    
    def _sanitize_doc_id(self, name: str) -> str:
        """Firestore Document IDに適した形式に変換"""
        sanitized = re.sub(r'[/\\#?&]', '_', name)
        return sanitized[:1500] if len(sanitized) > 1500 else sanitized

