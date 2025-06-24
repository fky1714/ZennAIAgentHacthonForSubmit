from utils.logger import Logger
from typing import Dict, Any


from knowledge_graph import (
    FirestoreRepository,
    EntityExtractor,
    QueryAnalyzer,
    AnswerGenerator,
    KnowledgeGraphManager,
    SearchEngine
)

class KnowledgeGraphRAGService:
    """統合RAGサービス - 各コンポーネントを組み合わせる"""
    
    def __init__(self):
        self.repository = FirestoreRepository()
        self.entity_extractor = EntityExtractor()
        self.query_analyzer = QueryAnalyzer()
        self.answer_generator = AnswerGenerator()
        self.kg_manager = KnowledgeGraphManager(self.repository, self.entity_extractor)
        self.search_engine = SearchEngine(self.repository)
        self.logger = Logger(name=self.__class__.__name__)
    
    def build_knowledge_graph_from_existing_data(self, uid: str) -> Dict[str, Any]:
        """既存データからナレッジグラフを構築"""
        return self.kg_manager.build_graph_from_existing_data(uid)
    
    def update_knowledge_graph(self, uid: str, doc_id: str, title: str, content: str, doc_type: str):
        """ナレッジグラフを更新"""
        return self.kg_manager.update_knowledge_graph(uid, doc_id, title, content, doc_type)
    
    def generate_query_and_search(self, uid: str, user_message: str) -> Dict[str, Any]:
        """クエリ処理と検索"""
        self.logger.info(f"Processing query for user {uid}: {user_message}")
        
        # クエリ分析
        query_analysis = self.query_analyzer.analyze_query(user_message)
        
        # 関連エンティティ検索
        relevant_entities = self.search_engine.search_relevant_entities(uid, query_analysis)
        
        # 関連ドキュメント取得
        relevant_documents = self.search_engine.get_relevant_documents(uid, relevant_entities, query_analysis)
        
        # 関係性情報取得
        relationships = self.search_engine.get_relevant_relationships(uid, relevant_entities)
        
        # 回答生成
        answer = self.answer_generator.generate_answer(
            user_message, relevant_documents, relationships, query_analysis
        )
        
        return answer
    

