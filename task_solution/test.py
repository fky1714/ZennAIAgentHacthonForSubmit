from services.ai_chat_service import KnowledgeGraphRAGService


if __name__ == "__main__":
    kg_service = KnowledgeGraphRAGService()
    uid = "115948075866126462669"
    kg_service.build_knowledge_graph_from_existing_data(uid=uid)