from typing import List, Dict, Any
from google.cloud import firestore
from utils.logger import Logger
import re

from .firestore_repository import FirestoreRepository
from .ai import EntityExtractor

class KnowledgeGraphManager:
    """ナレッジグラフの管理を担当"""
    
    def __init__(self, repository: FirestoreRepository, entity_extractor: EntityExtractor):
        self.repository = repository
        self.entity_extractor = entity_extractor
        self.logger = Logger(name=self.__class__.__name__)
    
    def build_graph_from_existing_data(self, uid: str) -> Dict[str, Any]:
        """既存データからナレッジグラフを構築"""
        self.logger.info(f"Building knowledge graph for user: {uid}")
        
        stats = {
            "reports_processed": 0,
            "procedures_processed": 0,
            "entities_created": 0,
            "relations_created": 0,
            "errors": []
        }
        
        try:
            # 既存グラフをクリア
            self._clear_existing_graph(uid)
            
            # レポート処理
            reports = self.repository.get_user_reports(uid)
            for report in reports:
                try:
                    self.update_knowledge_graph(
                        uid=uid,
                        doc_id=report["id"],
                        title=report.get("title", ""),
                        content=report.get("content", ""),
                        doc_type="report"
                    )
                    stats["reports_processed"] += 1
                except Exception as e:
                    stats["errors"].append(f"Report {report['id']}: {str(e)}")
                    self.logger.error(f"Error processing report {report['id']}: {e}")
            
            # 手順処理
            procedures = self.repository.get_user_procedures(uid)
            for procedure in procedures:
                try:
                    self.update_knowledge_graph(
                        uid=uid,
                        doc_id=procedure["id"],
                        title=procedure["id"],
                        content=procedure.get("content", ""),
                        doc_type="procedure"
                    )
                    stats["procedures_processed"] += 1
                except Exception as e:
                    stats["errors"].append(f"Procedure {procedure['id']}: {str(e)}")
                    self.logger.error(f"Error processing procedure {procedure['id']}: {e}")
            
            # 統計更新
            stats["entities_created"] = self.repository.get_collection_count(uid, "entities")
            stats["relations_created"] = self.repository.get_collection_count(uid, "relations")
            
            self.logger.info(f"Knowledge graph built successfully: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Error building knowledge graph: {e}")
            stats["errors"].append(f"System error: {str(e)}")
            return stats
    
    def update_knowledge_graph(self, uid: str, doc_id: str, title: str, content: str, doc_type: str):
        """ナレッジグラフを更新"""
        self.logger.info(f"Updating knowledge graph: {doc_type} - {title}")
        
        try:
            # エンティティと関係を抽出
            extracted = self.entity_extractor.extract_entities_and_relations(title, content, doc_type)
            
            # ドキュメントノードを保存
            node = {
                "id": doc_id,
                "title": title,
                "content": content,
                "type": doc_type,
                "created_at": firestore.SERVER_TIMESTAMP,
                "last_updated": firestore.SERVER_TIMESTAMP
            }
            self.repository.save_knowledge_node(uid, node, f"{doc_type}_{doc_id}")
            
            # エンティティを処理
            self._process_entities(uid, extracted.get("entities", []), doc_id, title, doc_type)
            
            # 関係を処理
            self._process_relationships(uid, extracted.get("relationships", []), doc_id, doc_type)
            
            self.logger.info(f"Successfully updated knowledge graph for {doc_type}: {title}")
            
        except Exception as e:
            self.logger.error(f"Error updating knowledge graph: {e}")
            raise
    
    def _clear_existing_graph(self, uid: str):
        """既存グラフをクリア"""
        collections = ["knowledge_nodes", "entities", "relations"]
        for collection_name in collections:
            self.repository.clear_collection(uid, collection_name)
    
    def _process_entities(self, uid: str, entities: List[Dict[str, Any]], doc_id: str, title: str, doc_type: str):
        """エンティティを処理"""
        for entity in entities:
            entity_name = entity["name"]
            existing_entity = self.repository.get_entity(uid, entity_name)
            
            if existing_entity:
                # 既存エンティティを更新
                existing_entity[f"mentioned_in.{doc_type}_{doc_id}"] = {
                    "title": title,
                    "doc_type": doc_type,
                    "timestamp": firestore.SERVER_TIMESTAMP
                }
                existing_entity["last_updated"] = firestore.SERVER_TIMESTAMP
                existing_entity["properties"] = {**existing_entity.get("properties", {}), 
                                               **entity.get("properties", {})}
            else:
                # 新規エンティティを作成
                existing_entity = {
                    "name": entity_name,
                    "type": entity["type"],
                    "properties": entity.get("properties", {}),
                    "mentioned_in": {
                        f"{doc_type}_{doc_id}": {
                            "title": title,
                            "doc_type": doc_type,
                            "timestamp": firestore.SERVER_TIMESTAMP
                        }
                    },
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "last_updated": firestore.SERVER_TIMESTAMP
                }
            
            self.repository.save_entity(uid, existing_entity)
    
    def _process_relationships(self, uid: str, relationships: List[Dict[str, Any]], doc_id: str, doc_type: str):
        """関係を処理"""
        for rel in relationships:
            relation_id = self._generate_relation_id(rel["from"], rel["to"], rel["type"])
            existing_relation = self.repository.get_relation(uid, relation_id)
            
            if existing_relation:
                # 既存関係を強化
                current_strength = existing_relation.get("strength", 0)
                new_strength = min(current_strength + rel.get("properties", {}).get("strength", 0.5), 1.0)
                
                existing_relation.update({
                    "strength": new_strength,
                    "contexts": list(set(existing_relation.get("contexts", []) + [doc_type])),
                    "source_documents": list(set(existing_relation.get("source_documents", []) + [f"{doc_type}_{doc_id}"])),
                    "last_updated": firestore.SERVER_TIMESTAMP
                })
            else:
                # 新規関係を作成
                existing_relation = {
                    "from_entity": rel["from"],
                    "to_entity": rel["to"],
                    "relation_type": rel["type"],
                    "strength": rel.get("properties", {}).get("strength", 0.5),
                    "contexts": [doc_type],
                    "source_documents": [f"{doc_type}_{doc_id}"],
                    "properties": rel.get("properties", {}),
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "last_updated": firestore.SERVER_TIMESTAMP
                }
            
            self.repository.save_relation(uid, existing_relation, relation_id)
    
    def _generate_relation_id(self, from_entity: str, to_entity: str, relation_type: str) -> str:
        """関係IDを生成"""
        from_sanitized = re.sub(r'[/\\#?&]', '_', from_entity)[:500]
        to_sanitized = re.sub(r'[/\\#?&]', '_', to_entity)[:500]
        return f"{from_sanitized}_{relation_type}_{to_sanitized}"[:1500]


class SearchEngine:
    """検索機能を担当"""
    
    def __init__(self, repository: FirestoreRepository):
        self.repository = repository
        self.logger = Logger(name=self.__class__.__name__)
    
    def search_relevant_entities(self, uid: str, query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """関連エンティティを検索"""
        relevant_entities = []
        
        try:
            for keyword in query_analysis.get("keywords", []):
                entities = self.repository.search_entities_by_keyword(uid, keyword)
                
                for entity in entities:
                    entity["relevance_score"] = self._calculate_entity_relevance(entity, query_analysis)
                    relevant_entities.append(entity)
            
            # エンティティタイプフィルタリング
            if query_analysis.get("entity_types"):
                for entity in relevant_entities:
                    if entity.get("type") in query_analysis["entity_types"]:
                        entity["relevance_score"] += 0.2
            
            # 重複除去とソート
            seen_entities = set()
            unique_entities = []
            
            for entity in sorted(relevant_entities, key=lambda x: x.get("relevance_score", 0), reverse=True):
                if entity["name"] not in seen_entities:
                    seen_entities.add(entity["name"])
                    unique_entities.append(entity)
            
            return unique_entities[:10]
            
        except Exception as e:
            self.logger.error(f"Error searching entities: {e}")
            return []
    
    def get_relevant_documents(self, uid: str, relevant_entities: List[Dict[str, Any]], query_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """関連ドキュメントを取得"""
        relevant_docs = []
        seen_docs = set()
        
        try:
            for entity in relevant_entities:
                mentioned_in = entity.get("mentioned_in", {})
                
                for doc_ref, doc_info in mentioned_in.items():
                    if doc_ref not in seen_docs:
                        # フォーカスフィルタ
                        if query_analysis.get("focus") != "BOTH":
                            if doc_info.get("doc_type") != query_analysis["focus"].lower():
                                continue
                        
                        doc_data = self.repository.get_knowledge_node(uid, doc_ref)
                        if doc_data:
                            doc_data["relevance_score"] = entity.get("relevance_score", 0)
                            relevant_docs.append(doc_data)
                            seen_docs.add(doc_ref)
            
            return sorted(relevant_docs, key=lambda x: x.get("relevance_score", 0), reverse=True)[:5]
            
        except Exception as e:
            self.logger.error(f"Error getting relevant documents: {e}")
            return []
    
    def get_relevant_relationships(self, uid: str, relevant_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """関連する関係性を取得"""
        try:
            entity_names = {entity["name"] for entity in relevant_entities}
            all_relations = self.repository.get_all_relations(uid)
            
            relationships = []
            for rel_data in all_relations:
                if (rel_data.get("from_entity") in entity_names or 
                    rel_data.get("to_entity") in entity_names):
                    relationships.append(rel_data)
            
            return sorted(relationships, key=lambda x: x.get("strength", 0), reverse=True)[:10]
            
        except Exception as e:
            self.logger.error(f"Error getting relationships: {e}")
            return []
    
    def _calculate_entity_relevance(self, entity: Dict[str, Any], query_analysis: Dict[str, Any]) -> float:
        """エンティティの関連度を計算"""
        score = 0.0
        
        entity_name = entity.get("name", "").lower()
        for keyword in query_analysis.get("keywords", []):
            if keyword.lower() in entity_name:
                score += 0.5
        
        if entity.get("type") in query_analysis.get("entity_types", []):
            score += 0.3
        
        mentioned_in = entity.get("mentioned_in", {})
        if len(mentioned_in) > 1:
            score += 0.2
        
        return score
