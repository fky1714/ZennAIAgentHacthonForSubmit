# task_solution/agents/rag_chatbot_agent.py

import os
from google.cloud import firestore_v1
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure as FirestoreDistanceMeasure # Corrected Import
# For text generation, we can use the model from BaseVertexAI or TextGenerationModel directly
from vertexai.preview.language_models import TextEmbeddingModel, TextEmbeddingInput # Using preview
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig # For Gemini (used in BaseVertexAI)

from .vertex_ai.base_vertex_ai import BaseVertexAI
from utils.logger import Logger # Assuming a logger utility exists

# Define DistanceMeasure if not readily available or for clarity
# from google.cloud.firestore_v1.types import DistanceMeasure # This might be the path

class RagChatbotAgent(BaseVertexAI):
    def __init__(
        self,
        firestore_collection: str = "rag_chunks_all",
        embedding_model_name: str = "gemini-embedding-001", # Using gemini-embedding-001
        generation_model_name: str = "gemini-1.0-pro",
        project_id: str = None,
        location: str = None,
        top_k: int = 5,
        distance_measure: str = "COSINE", # COSINE, EUCLIDEAN, DOT_PRODUCT
    ):
        super().__init__(model_name=generation_model_name) # Initialize BaseVertexAI with the generation model
        self.logger = Logger(name=self.__class__.__name__).get_logger()

        if project_id is None:
            project_id = os.getenv("GCP_PROJECT")
        if location is None:
            location = os.getenv("GCP_LOCATION", "us-central1") # Default location for Vertex AI

        if not project_id:
            self.logger.error("GCP_PROJECT environment variable or project_id parameter must be set.")
            raise ValueError("GCP_PROJECT environment variable or project_id parameter must be set.")

        self.db = firestore_v1.Client(project=project_id)
        self.firestore_collection = firestore_collection
        self.logger.info(f"Firestore client initialized for project: {project_id}, collection: {self.firestore_collection}")

        try:
            self.embedding_model = TextEmbeddingModel.from_pretrained(embedding_model_name)
            self.logger.info(f"TextEmbeddingModel '{embedding_model_name}' initialized.")
        except Exception as e:
            self.logger.error(f"Failed to initialize TextEmbeddingModel '{embedding_model_name}': {e}")
            raise

        self.top_k = top_k

        # Convert distance_measure string to Enum
        dm_upper = distance_measure.upper()
        if dm_upper == "COSINE":
            self.distance_measure_enum = FirestoreDistanceMeasure.COSINE
        elif dm_upper == "EUCLIDEAN":
            self.distance_measure_enum = FirestoreDistanceMeasure.EUCLIDEAN
        elif dm_upper == "DOT_PRODUCT":
            self.distance_measure_enum = FirestoreDistanceMeasure.DOT_PRODUCT
        else:
            self.logger.error(f"Invalid distance_measure string: {distance_measure}. Must be COSINE, EUCLIDEAN, or DOT_PRODUCT.")
            raise ValueError(f"Invalid distance_measure: {distance_measure}. Must be COSINE, EUCLIDEAN, or DOT_PRODUCT.")

        self.rag_generation_config = GenerationConfig(
            response_mime_type="text/plain"
        )
        self.logger.info(f"RagChatbotAgent initialized with embedding_model: {embedding_model_name}, generation_model: {generation_model_name}, top_k: {top_k}, distance_measure: {self.distance_measure_enum.name}")

    def get_rag_response(self, question: str) -> str:
        self.logger.info(f"Received question: {question}")

        try:
            query_embedding_input = TextEmbeddingInput(
                text=question,
                task_type="RETRIEVAL_QUERY"  # Specify task_type for RAG query
            )
            # Ensure self.embedding_model is initialized correctly in __init__
            query_embeddings_response = self.embedding_model.get_embeddings([query_embedding_input])

            if not query_embeddings_response or \
               not hasattr(query_embeddings_response[0], 'values') or \
               not query_embeddings_response[0].values:
                self.logger.error(f"Failed to get embeddings for the question. Response: {str(query_embeddings_response)[:200]}")
                return "申し訳ありませんが、質問を処理できませんでした。"

            query_vector_values = query_embeddings_response[0].values

            # Optional: Check dimension if you know what gemini-embedding-001 should return (e.g., 768)
            # expected_dimension = 768
            # if len(query_vector_values) != expected_dimension:
            #     self.logger.warning(f"Query embedding dimension is {len(query_vector_values)}, expected {expected_dimension} for {self.embedding_model._model_id_component()}. Proceeding, but this might indicate an issue.")

            query_vector = Vector(query_vector_values)
            self.logger.debug(f"Query vector generated (first 3 values): {str(query_vector_values[:3])}...")
        except Exception as e:
            self.logger.error(f"Error generating query embedding: {e}", exc_info=True) # Added exc_info for more details
            return "申し訳ありませんが、質問のベクトル化中にエラーが発生しました。"

        try:
            collection_ref = self.db.collection(self.firestore_collection)
            nearest_docs_query = collection_ref.find_nearest(
                vector_field="embedding",
                query_vector=query_vector,
                distance_measure=self.distance_measure_enum, # Use Enum here
                limit=self.top_k,
            )
            snapshot = nearest_docs_query.get()
            self.logger.info(f"Found {len(snapshot.documents)} documents from Firestore.")
        except Exception as e:
            self.logger.error(f"Error during Firestore vector search: {e}")
            if "no matching index found" in str(e).lower():
                self.logger.error("Firestore vector index might not be configured for the 'embedding' field in collection '{self.firestore_collection}'.")
                return f"関連情報を見つけるためのインデックスがコレクション '{self.firestore_collection}' に設定されていないようです。管理者にご確認ください。"
            return "申し訳ありませんが、関連情報の検索中にエラーが発生しました。"

        contexts = []
        if snapshot.documents:
            for doc in snapshot.documents:
                doc_data = doc.to_dict()
                if "text" in doc_data:
                    contexts.append(str(doc_data["text"])) # Ensure text is string
                else:
                    self.logger.warning(f"Document {doc.id} in '{self.firestore_collection}' missing 'text' field.")
            context_string = "\n---\n".join(contexts)
            self.logger.debug(f"Context string created: {context_string[:200]}...")
        else:
            context_string = "関連する情報は見つかりませんでした。"
            self.logger.info("No relevant documents found to create context.")

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
                [prompt],
                generation_config=self.rag_generation_config
            )
            answer = llm_response.text
            self.logger.info(f"LLM generated answer: {answer[:200]}...")
        except Exception as e:
            self.logger.error(f"Error generating answer with LLM: {e}")
            return "申し訳ありませんが、回答の生成中にエラーが発生しました。"

        return answer

if __name__ == '__main__':
    print("Attempting to initialize RagChatbotAgent for testing...")

    gcp_project_id = os.getenv("GCP_PROJECT")
    if not gcp_project_id:
        print("Please set the GCP_PROJECT environment variable for testing.")
        print("Example: export GCP_PROJECT=\"your-gcp-project-id\"")
        exit(1)
    print(f"Using GCP_PROJECT: {gcp_project_id}")

    # Ensure application default credentials are set up
    # `gcloud auth application-default login`
    # Or GOOGLE_APPLICATION_CREDENTIALS environment variable points to a service account key file.

    try:
        # Agent uses default "rag_chunks_all" and "gemini-embedding-001" from its __init__
        agent = RagChatbotAgent(
            project_id=gcp_project_id,
            top_k=3
        )
        print("RagChatbotAgent initialized successfully.")

        # Before running this test block:
        # 1. Ensure `prepare_rag_data.py` has been run for some UID(s) to populate "rag_chunks_all".
        # 2. Ensure `create_firestore_index.sh` has been run and the index for "rag_chunks_all" is active.
        # 3. Set GCP_PROJECT environment variable.

        # --- Test Question 1: Firestoreのデータに関連する具体的な質問 ---
        # 例: 実際にprepare_rag_data.pyで処理したレポートのタイトルや手順名に関する質問
        #    以下の質問は、ログにあったレポートタイトルを参考にしています。
        #    実際に投入したデータに合わせて調整してください。
        question1 = "AIシステム「Sofia」紹介動画の作成について、概要を教えてください。"
        print(f"\nTesting with question 1: '{question1}'")
        response1 = agent.get_rag_response(question1)
        print(f"\nResponse 1:\n{response1}")

        # --- Test Question 2: Firestoreのデータに部分的に関連するかもしれない曖昧な質問 ---
        question2 = "デモ動画の作成に関する一般的な注意点は何ですか？" # Sofia以外のデモ動画の可能性も
        print(f"\nTesting with question 2: '{question2}'")
        response2 = agent.get_rag_response(question2)
        print(f"\nResponse 2:\n{response2}")

        # --- Test Question 3: Firestoreのデータに全く関連しない質問 ---
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
