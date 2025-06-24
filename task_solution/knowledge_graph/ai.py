import json
from typing import List, Dict, Any

from ..agents.vertex_ai.base_vertex_ai import BaseVertexAI # Changed import path
from ..utils.logger import Logger # Changed import path


class EntityExtractor(BaseVertexAI):
    """エンティティと関係の抽出を担当"""
    
    def __init__(self, model_name="gemini-1.5-flash-001"):
        super().__init__(model_name=model_name)
        # self.logger is initialized in the superclass BaseVertexAI.

        self.response_scheme = {
            "type": "OBJECT",
            "properties": {
                "entities": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "name": {"type": "STRING"},
                            "type": {"type": "STRING"},
                            "properties": {
                                "type": "OBJECT",
                                "properties": {
                                    "confidence": {"type": "NUMBER"},
                                    "category": {"type": "STRING"},
                                    "description": {"type": "STRING"}
                                },
                                "required": ["confidence", "category", "description"]
                            }
                        },
                        "required": ["name", "type", "properties"]
                    }
                },
                "relationships": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "from": {"type": "STRING"},
                            "to": {"type": "STRING"},
                            "type": {"type": "STRING"},
                            "properties": {
                                "type": "OBJECT",
                                "properties": {
                                    "strength": {"type": "NUMBER"},
                                    "context": {"type": "STRING"},
                                    "description": {"type": "STRING"}
                                },
                                "required": ["strength", "context", "description"]
                            }
                        },
                        "required": ["from", "to", "type", "properties"]
                    }
                }
            },
            "required": ["entities", "relationships"]
        }
    
    def extract_entities_and_relations(self, title: str, content: str, doc_type: str) -> Dict[str, Any]:
        """エンティティと関係を抽出"""
        context, focus, entity_types, relation_types = self._get_extraction_config(doc_type)
        
        # Vertex AI expects a list of Parts or strings.
        # For Gemini, the prompt structure is simpler.
        # We will construct a single prompt string.
        prompt = f"""\
{context}重要なエンティティと関係を抽出してください。
特に{focus}に注目してください。

タイトル: {title}
内容: {content}

以下のJSON形式で出力してください：
{{
    "entities": [
        {{
            "name": "エンティティ名（具体的で一意な名前）", 
            "type": "{entity_types}から選択", 
            "properties": {{"confidence": 0.8, "category": "カテゴリ", "description": "簡潔な説明"}}
        }}
    ],
    "relationships": [
        {{
            "from": "エンティティ1", 
            "to": "エンティティ2", 
            "type": "{relation_types}から選択", 
            "properties": {{"strength": 0.8, "context": "{doc_type}", "description": "関係の説明"}}
        }}
    ]
}}

重要：
- エンティティ名は具体的で重複しないように
- 関係は方向性を明確に
- 重要度の高いもの（上位5-10個）のみ抽出
"""
        
        try:
            # self.invoke will use the generation_config including the response_schema
            response = self.invoke(prompt)
            
            # The response text should be a JSON string based on response_schema
            result = json.loads(response.text)
            self.logger.info(f"Extracted {len(result.get('entities', []))} entities and {len(result.get('relationships', []))} relationships")
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            # Consider if more specific error handling for Vertex AI is needed
            return {"entities": [], "relationships": []}
    
    def _get_extraction_config(self, doc_type: str) -> tuple:
        """ドキュメントタイプに応じた抽出設定を取得"""
        if doc_type == "report":
            return (
                "このレポートから",
                "分析結果、データ、結論、要因、指標、問題点",
                "METRIC|FACTOR|RESULT|ISSUE|TREND|INSIGHT|TOOL|PERSON|ORGANIZATION",
                "CAUSES|CORRELATES_WITH|INDICATES|SHOWS|MENTIONS|USES|AFFECTS"
            )
        else:  # procedure
            return (
                "この手順から",
                "ステップ、ツール、条件、成果物、前提条件、手順",
                "STEP|TOOL|CONDITION|OUTPUT|INPUT|REQUIREMENT|RESOURCE|ACTION",
                "REQUIRES|PRODUCES|USES|LEADS_TO|DEPENDS_ON|MENTIONS|ENABLES"
            )


class QueryAnalyzer(BaseVertexAI):
    """クエリ分析を担当"""
    
    def __init__(self, model_name="gemini-1.5-flash-001"):
        super().__init__(model_name=model_name)
        # self.logger is initialized in the superclass BaseVertexAI.

        self.response_scheme = {
            "type": "OBJECT",
            "properties": {
                "query_type": {"type": "STRING", "enum": ["HOW_TO", "ANALYSIS", "COMPARISON", "TROUBLESHOOTING", "GENERAL"]},
                "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
                "focus": {"type": "STRING", "enum": ["PROCEDURE", "REPORT", "BOTH"]},
                "entity_types": {"type": "ARRAY", "items": {"type": "STRING"}},
                "search_intent": {"type": "STRING"},
                "priority": {"type": "STRING", "enum": ["HIGH", "MEDIUM", "LOW"]}
            },
            "required": ["query_type", "keywords", "focus", "entity_types", "search_intent", "priority"]
        }
    
    def analyze_query(self, user_message: str) -> Dict[str, Any]:
        """ユーザークエリの意図分析"""
        prompt = f"""
以下のユーザーメッセージを分析して、検索意図を特定してください：

ユーザーメッセージ: {user_message}

以下のJSON形式で出力してください：
{{
    "query_type": "HOW_TO|ANALYSIS|COMPARISON|TROUBLESHOOTING|GENERAL",
    "keywords": ["重要キーワード1", "重要キーワード2", "重要キーワード3"],
    "focus": "PROCEDURE|REPORT|BOTH",
    "entity_types": ["TOOL", "STEP", "RESULT", "ISSUE"],
    "search_intent": "何を探しているかの説明",
    "priority": "HIGH|MEDIUM|LOW"
}}
"""
        
        try:
            response = self.invoke(prompt)
            result = json.loads(response.text)
            return result
        except Exception as e:
            self.logger.error(f"Error analyzing query: {e}")
            # Fallback to a default response structure
            return {
                "query_type": "GENERAL",
                "keywords": [user_message[:50]], # Keep original slicing for safety
                "focus": "BOTH",
                "entity_types": [],
                "search_intent": user_message,
                "priority": "MEDIUM"
            }


class AnswerGenerator(BaseVertexAI):
    """回答生成を担当"""
    
    def __init__(self, model_name="gemini-1.5-flash-001"):
        super().__init__(model_name=model_name)
        # self.logger is initialized in the superclass BaseVertexAI.
        # No response_scheme is set, so BaseVertexAI will default to text/plain.
    
    def generate_answer(self, user_message: str, documents: List[Dict[str, Any]], 
                       relationships: List[Dict[str, Any]], query_analysis: Dict[str, Any]) -> str:
        """統合回答を生成"""
        
        if not documents and not relationships : # If no context, don't call API
            return "申し訳ございませんが、ご質問に関連する情報が見つかりませんでした。"
        
        unified_context = self._build_context(documents, relationships)
        
        prompt = f"""
以下のナレッジベースから、ユーザーの質問に対して具体的で実用的な回答を提供してください：

{unified_context}

質問: {user_message}
質問の意図: {query_analysis.get('search_intent', '特になし')}

回答の要件：
1. 分析結果と手順を適切に組み合わせて回答
2. 具体的で実行可能なアドバイスを含める
3. 関係性の情報も活用して包括的に回答
4. 参考にした情報源を明記 (例: 【タイトル】)
5. 日本語で自然な文章で回答

回答:
"""
        
        try:
            response = self.invoke(prompt)
            # For text/plain, the response is directly in response.text
            # No json.loads needed
            generated_text = response.text
            if not generated_text.strip():
                self.logger.warning("Generated answer was empty or whitespace.")
                return "回答を生成できませんでした。もう一度お試しください。"
            return generated_text
            
        except Exception as e:
            self.logger.error(f"Error generating answer: {e}")
            return "回答生成中にエラーが発生しました。申し訳ございませんが、管理者にお問い合わせください。"
    
    def _build_context(self, documents: List[Dict[str, Any]], relationships: List[Dict[str, Any]]) -> str:
        """コンテキストを構築"""
        context_parts = []
        
        reports = [doc for doc in documents if doc.get("type") == "report"]
        procedures = [doc for doc in documents if doc.get("type") == "procedure"]
        
        if reports:
            context_parts.append("=== 関連分析・レポート ===")
            for report in reports[:2]:
                context_parts.append(f"【{report.get('title', 'タイトルなし')}】")
                context_parts.append(f"{report.get('content', '')[:600]}...")
        
        if procedures:
            context_parts.append("\n=== 関連手順・プロセス ===")
            for procedure in procedures[:2]:
                context_parts.append(f"【{procedure.get('title', 'タイトルなし')}】")
                context_parts.append(f"{procedure.get('content', '')[:600]}...")
        
        if relationships:
            context_parts.append("\n=== 重要な関係性 ===")
            for rel in relationships[:5]:
                context_parts.append(
                    f"• {rel.get('from_entity', '')} -{rel.get('relation_type', '')}- {rel.get('to_entity', '')} "
                    f"(関連度: {rel.get('strength', 0):.2f})"
                )
        
        return "\n".join(context_parts)


