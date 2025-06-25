# task_solution/agents/rag_chatbot_agent.py

import os
import vertexai  # Ensure vertexai is imported for init
from google.cloud import firestore_v1
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import (
    DistanceMeasure as FirestoreDistanceMeasure,
)
from vertexai.preview.language_models import (
    TextEmbeddingModel,
    TextEmbeddingInput,
)  # Using preview
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig

from .vertex_ai.base_vertex_ai import BaseVertexAI
from utils.logger import Logger  # Assuming a logger utility exists


class RagChatbotAgent(BaseVertexAI):
    def __init__(
        self,
        firestore_collection: str = "rag_chunks_all",
        embedding_model_name: str = "text-embedding-004",  # Changed to use text-embedding-004 (768 dims)
        generation_model_name: str = "gemini-2.0-flash",
        project_id: str = None,
        location: str = None,
        top_k: int = 5,
        distance_measure: str = "COSINE",  # COSINE, EUCLIDEAN, DOT_PRODUCT
    ):
        super().__init__(model_name=generation_model_name)
        self.logger = Logger(name=self.__class__.__name__).get_logger()

        _project_id = project_id if project_id else os.getenv("GCP_PROJECT")
        _location = location if location else os.getenv("GCP_LOCATION", "us-central1")

        if not _project_id:
            self.logger.error(
                "GCP_PROJECT environment variable or project_id parameter must be set for RagChatbotAgent."
            )
            raise ValueError(
                "GCP_PROJECT environment variable or project_id parameter must be set."
            )

        try:
            self.logger.info(
                f"Explicitly initializing Vertex AI for RagChatbotAgent with project:{_project_id}, location:{_location}"
            )
            vertexai.init(project=_project_id, location=_location)
        except Exception as e:
            self.logger.error(
                f"Error during explicit vertexai.init() in RagChatbotAgent: {e}",
                exc_info=True,
            )
            raise

        self.db = firestore_v1.Client(project=_project_id)
        self.firestore_collection = firestore_collection
        self.logger.info(
            f"Firestore client initialized for project: {_project_id}, collection: {self.firestore_collection}"
        )

        try:
            self.embedding_model = TextEmbeddingModel.from_pretrained(
                embedding_model_name
            )
            self.logger.info(
                f"TextEmbeddingModel '{embedding_model_name}' initialized."
            )
        except Exception as e:
            self.logger.error(
                f"Failed to initialize TextEmbeddingModel '{embedding_model_name}': {e}",
                exc_info=True,
            )
            raise

        self.top_k = top_k
        self.embedding_model_name = embedding_model_name

        # Set expected dimensions based on model
        self.expected_dimensions = self._get_expected_dimensions(embedding_model_name)

        # Convert distance_measure string to Enum
        dm_upper = distance_measure.upper()
        if dm_upper == "COSINE":
            self.distance_measure_enum = FirestoreDistanceMeasure.COSINE
        elif dm_upper == "EUCLIDEAN":
            self.distance_measure_enum = FirestoreDistanceMeasure.EUCLIDEAN
        elif dm_upper == "DOT_PRODUCT":
            self.distance_measure_enum = FirestoreDistanceMeasure.DOT_PRODUCT
        else:
            self.logger.error(
                f"Invalid distance_measure string: {distance_measure}. Must be COSINE, EUCLIDEAN, or DOT_PRODUCT."
            )
            raise ValueError(
                f"Invalid distance_measure: {distance_measure}. Must be COSINE, EUCLIDEAN, or DOT_PRODUCT."
            )

        self.rag_generation_config = GenerationConfig(response_mime_type="text/plain")
        self.logger.info(
            f"RagChatbotAgent initialized with embedding_model: {embedding_model_name}, generation_model: {generation_model_name}, top_k: {top_k}, distance_measure: {self.distance_measure_enum.name}, expected_dims: {self.expected_dimensions}"
        )

    def _get_expected_dimensions(self, model_name: str) -> int:
        """Get expected embedding dimensions for different models."""
        model_dimensions = {
            "text-embedding-004": 768,
            "text-multilingual-embedding-002": 768,
            "textembedding-gecko@003": 768,
            "textembedding-gecko@002": 768,
            "textembedding-gecko@001": 768,
            "text-embedding-preview-0409": 768,
            "gemini-embedding-001": 3072,  # This is actually 3072, too large for Firestore
        }
        return model_dimensions.get(model_name, 768)

    def _get_embedding_input_params(self, text: str, model_name: str) -> dict:
        """Get appropriate parameters for TextEmbeddingInput based on model."""
        if "text-embedding" in model_name or "textembedding-gecko" in model_name:
            return {"text": text, "task_type": "RETRIEVAL_QUERY"}
        elif "gemini-embedding" in model_name:
            return {"text": text, "task_type": "RETRIEVAL_QUERY"}
        else:
            # Default params
            return {"text": text, "task_type": "RETRIEVAL_QUERY"}

    def get_rag_response(self, question: str) -> str:
        self.logger.info(f"Received question: {question}")

        try:
            # Get appropriate input parameters for the model
            input_params = self._get_embedding_input_params(
                question, self.embedding_model_name
            )
            query_embedding_input = TextEmbeddingInput(**input_params)

            query_embeddings_response = self.embedding_model.get_embeddings(
                [query_embedding_input]
            )

            if (
                not query_embeddings_response
                or not hasattr(query_embeddings_response[0], "values")
                or not query_embeddings_response[0].values
            ):
                self.logger.error(
                    f"Failed to get embeddings for the question. Response: {str(query_embeddings_response)[:200]}"
                )
                return "申し訳ありませんが、質問を処理できませんでした。"

            query_vector_values = query_embeddings_response[0].values

            query_emb_len = (
                len(query_vector_values)
                if hasattr(query_vector_values, "__len__")
                else -1
            )
            self.logger.info(
                f"Query embedding details: type={type(query_vector_values)}, length={query_emb_len}, first_3_values={str(query_vector_values[:3]) if query_emb_len > 0 else 'N/A'}"
            )

            # Check if dimensions match expected
            if query_emb_len != self.expected_dimensions:
                self.logger.error(
                    f"CRITICAL: Query embedding dimension is {query_emb_len}, expected {self.expected_dimensions} for {self.embedding_model_name}."
                )

            # Check Firestore limit
            if query_emb_len > 2048:
                self.logger.error(
                    f"CRITICAL: Query embedding dimension is {query_emb_len}, but Firestore supports max 2048 dimensions."
                )
                return "申し訳ありませんが、使用している埋め込みモデルがFirestoreの制限を超えています。管理者にご確認ください。"

            query_vector = Vector(query_vector_values)
        except Exception as e:
            self.logger.error(f"Error generating query embedding: {e}", exc_info=True)
            return "申し訳ありませんが、質問のベクトル化中にエラーが発生しました。"

        try:
            collection_ref = self.db.collection(self.firestore_collection)
            nearest_docs_query = collection_ref.find_nearest(
                vector_field="embedding",
                query_vector=query_vector,
                distance_measure=self.distance_measure_enum,
                limit=self.top_k,
            )
            docs = nearest_docs_query.stream()
            # self.logger.info(f"Found {len(snapshot)} documents from Firestore.")
        except Exception as e:
            self.logger.error(f"Error during Firestore vector search: {e}")
            if "no matching index found" in str(e).lower():
                self.logger.error(
                    f"Firestore vector index might not be configured for the 'embedding' field in collection '{self.firestore_collection}'."
                )
                return f"関連情報を見つけるためのインデックスがコレクション '{self.firestore_collection}' に設定されていないようです。管理者にご確認ください。"
            elif "dimensions" in str(e).lower():
                self.logger.error(f"Dimension mismatch error: {e}")
                return "申し訳ありませんが、埋め込みベクトルの次元に問題があります。管理者にご確認ください。"
            return "申し訳ありませんが、関連情報の検索中にエラーが発生しました。"

        contexts = []
        for doc in docs:
            doc_data = doc.to_dict()
            if "text" in doc_data:
                contexts.append(str(doc_data["text"]))
            else:
                self.logger.warning(
                    f"Document {doc.id} in '{self.firestore_collection}' missing 'text' field."
                )
        context_string = "\n---\n".join(contexts)
        self.logger.info(f"Context string created: {context_string[:200]}...")

        prompt = f"""以下の提供された情報を参考にして、ユーザーの質問に日本語で回答してください。
提供された情報に質問への直接的な答えが含まれていない場合は、その旨を正直に伝えてください。憶測で答えないでください。

[提供情報]
{context_string}
---
[ユーザーの質問]
{question}

[回答]
"""
        self.logger.debug(f"Generated prompt for LLM: {prompt[:300]}...")

        try:
            llm_response = self.model.generate_content(
                [prompt], generation_config=self.rag_generation_config
            )
            answer = llm_response.text
            self.logger.info(f"LLM generated answer: {answer[:200]}...")
        except Exception as e:
            self.logger.error(f"Error generating answer with LLM: {e}")
            return "申し訳ありませんが、回答の生成中にエラーが発生しました。"

        return answer


if __name__ == "__main__":
    print("Attempting to initialize RagChatbotAgent for testing...")

    gcp_project_id = os.getenv("GCP_PROJECT")
    if not gcp_project_id:
        print("Please set the GCP_PROJECT environment variable for testing.")
        print('Example: export GCP_PROJECT="your-gcp-project-id"')
        exit(1)
    print(f"Using GCP_PROJECT: {gcp_project_id}")

    try:
        # Using text-embedding-004 which produces 768-dimensional embeddings
        agent = RagChatbotAgent(
            project_id=gcp_project_id,
            embedding_model_name="text-embedding-004",  # Changed from gemini-embedding-001
            top_k=3,
        )
        print("RagChatbotAgent initialized successfully.")

        # Test questions
        question1 = "AIシステム「Sofia」紹介動画の作成について、概要を教えてください。"
        print(f"\nTesting with question 1: '{question1}'")
        response1 = agent.get_rag_response(question1)
        print(f"\nResponse 1:\n{response1}")

        question2 = "デモ動画の作成に関する一般的な注意点は何ですか？"
        print(f"\nTesting with question 2: '{question2}'")
        response2 = agent.get_rag_response(question2)
        print(f"\nResponse 2:\n{response2}")

        question3 = "日本で一番高い山は何ですか？"
        print(f"\nTesting with question 3: '{question3}'")
        response3 = agent.get_rag_response(question3)
        print(f"\nResponse 3:\n{response3}")

    except ValueError as ve:
        print(f"Configuration Error: {ve}")
    except Exception as e:
        print(f"An error occurred during testing: {e}")
        import traceback

        traceback.print_exc()
