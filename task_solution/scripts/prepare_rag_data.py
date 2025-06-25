import argparse
import os
import sys
from typing import List, Dict, Any

# Add project root to sys.path to allow imports from task_solution
# This assumes the script is in task_solution/scripts/
project_root_candidates = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), # task_solution directory
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")) # One level above task_solution (if scripts is a subdir)
]
project_root = None
for pr_path in project_root_candidates:
    # Check if 'task_solution/services' exists from this path, indicating it's a valid root for imports
    if os.path.isdir(os.path.join(pr_path, "task_solution", "services")):
        project_root = pr_path
        break
    # Simpler check if the script is already within a recognizable structure
    if os.path.basename(pr_path) == "task_solution":
        project_root = os.path.dirname(pr_path) # The parent of task_solution
        break

if project_root and project_root not in sys.path:
    sys.path.insert(0, project_root)
if os.path.join(project_root, "task_solution") not in sys.path: # Ensure task_solution itself is accessible for relative imports if needed
     sys.path.insert(0, os.path.join(project_root, "task_solution"))


from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from vertexai.language_models import TextEmbeddingModel
from langchain.text_splitter import MarkdownTextSplitter
import vertexai # For vertexai.init()

from task_solution.services.firestore_service import FirestoreService
from task_solution.utils.logger import Logger


# --- Configuration ---
TARGET_RAG_COLLECTION_NAME = "rag_chunks_all"
EMBEDDING_MODEL_NAME = "gemini-embedding-001"  # Updated model name
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
FIRESTORE_BATCH_SIZE = 400

logger = Logger(name="prepare_rag_data").get_logger()

# Initialize services globally for the script
try:
    gcp_project_id = os.getenv("GCP_PROJECT")
    gcp_location = os.getenv("GCP_LOCATION", "us-central1")
    if not gcp_project_id:
        logger.error("GCP_PROJECT environment variable not set. Exiting.")
        sys.exit(1)

    vertexai.init(project=gcp_project_id, location=gcp_location)
    logger.info(f"Vertex AI initialized for project '{gcp_project_id}' and location '{gcp_location}'.")

    firestore_service = FirestoreService()
    db = firestore_service.db
    embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME) # Uses the updated model name
    logger.info(f"Successfully initialized Firestore service and Embedding model '{EMBEDDING_MODEL_NAME}'.")
except Exception as e:
    logger.error(f"Failed to initialize services: {e}", exc_info=True)
    sys.exit(1)

def get_all_reports(uid: str) -> List[Dict[str, Any]]:
    reports = []
    page = 1
    page_size = 50
    while True:
        try:
            # logger.debug(f"Fetching reports for UID {uid}, page {page}, page_size {page_size}")
            paged_reports = firestore_service.get_reports(uid, page=page, page_size=page_size)
            if not paged_reports:
                break
            reports.extend(paged_reports)
            page += 1
            if len(paged_reports) < page_size:
                break
        except Exception as e:
            logger.error(f"Error fetching reports for UID {uid} on page {page}: {e}", exc_info=True)
            break
    logger.info(f"Fetched {len(reports)} reports for UID {uid}.")
    return reports

def get_all_procedures(uid: str) -> List[Dict[str, Any]]:
    procedures = []
    page = 1
    page_size = 50
    while True:
        try:
            # logger.debug(f"Fetching procedures for UID {uid}, page {page}, page_size {page_size}")
            paged_procedures = firestore_service.get_procedures(uid, page=page, page_size=page_size)
            if not paged_procedures:
                break
            procedures.extend(paged_procedures)
            page += 1
            if len(paged_procedures) < page_size:
                break
        except Exception as e:
            logger.error(f"Error fetching procedures for UID {uid} on page {page}: {e}", exc_info=True)
            break
    logger.info(f"Fetched {len(procedures)} procedures for UID {uid}.")
    return procedures

def delete_existing_chunks(uid: str):
    logger.info(f"Deleting existing RAG chunks for UID: {uid} from '{TARGET_RAG_COLLECTION_NAME}'...")
    target_collection_ref = db.collection(TARGET_RAG_COLLECTION_NAME)
    query = target_collection_ref.where("metadata.original_uid", "==", uid)

    docs_snapshot = list(query.stream()) # Materialize the iterator to get a count
    total_to_delete = len(docs_snapshot)
    if total_to_delete == 0:
        logger.info(f"No existing RAG chunks found for UID: {uid}. Nothing to delete.")
        return

    logger.info(f"Found {total_to_delete} documents to delete for UID: {uid}.")

    batch = db.batch()
    deleted_count = 0
    for i, doc in enumerate(docs_snapshot):
        # logger.debug(f"  Adding delete for doc {doc.id} to batch.")
        batch.delete(doc.reference)
        deleted_count += 1
        if deleted_count % FIRESTORE_BATCH_SIZE == 0:
            batch.commit()
            logger.info(f"Committed batch delete, {deleted_count}/{total_to_delete} docs deleted so far.")
            batch = db.batch()

    if deleted_count % FIRESTORE_BATCH_SIZE != 0 and deleted_count > 0 :
        batch.commit()

    logger.info(f"Deleted {deleted_count} existing RAG chunks for UID: {uid}.")


def prepare_and_embed_chunks(text_content: str, splitter: MarkdownTextSplitter, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    chunks_with_embeddings = []
    source_text_identifier = metadata.get("title", metadata.get("original_doc_id", "Unknown source"))

    text_chunks = splitter.split_text(text_content)

    if not text_chunks:
        logger.warning(f"No text chunks generated for '{source_text_identifier}'. Skipping.")
        return []

    logger.info(f"Embedding {len(text_chunks)} chunks for '{source_text_identifier}' one by one...")
    successful_embeddings_count = 0
    for i, chunk_text in enumerate(text_chunks):
        try:
            # logger.debug(f"  Embedding chunk {i+1}/{len(text_chunks)} for '{source_text_identifier}'...")
            embedding_response = embedding_model.get_embeddings([chunk_text]) # Pass as a list

            if embedding_response and embedding_response[0].values:
                emb_val = embedding_response[0].values
                # Firestoreの次元数制限チェックをここで行うこともできる
                # if len(emb_val) > 2048:
                #    logger.error(f"  Embedding for chunk {i+1} of '{source_text_identifier}' has dimension {len(emb_val)}, which exceeds Firestore limit of 2048.")
                #    continue # スキップ

                chunk_doc = {
                    "text": chunk_text,
                    "embedding": Vector(emb_val),
                    "metadata": {
                        **metadata,
                        "chunk_index": i,
                        "chunk_total": len(text_chunks)
                    }
                }
                chunks_with_embeddings.append(chunk_doc)
                successful_embeddings_count +=1
            else:
                logger.error(f"  Failed to get embedding for chunk {i+1} of '{source_text_identifier}'. Response was: {embedding_response}")
        except Exception as e:
            logger.error(f"  Exception while embedding chunk {i+1} of '{source_text_identifier}': {e}", exc_info=True)
            # エラーが発生したチャンクはスキップ

    if successful_embeddings_count < len(text_chunks):
         logger.warning(f"Successfully embedded {successful_embeddings_count} out of {len(text_chunks)} chunks for '{source_text_identifier}'.")

    if not chunks_with_embeddings:
        logger.error(f"No chunks were successfully embedded for '{source_text_identifier}'.")

    return chunks_with_embeddings

def batch_write_to_firestore(chunks_to_write: List[Dict[str, Any]]):
    if not chunks_to_write:
        logger.info("No chunks to write to Firestore.")
        return

    logger.info(f"Starting batch write of {len(chunks_to_write)} chunks to '{TARGET_RAG_COLLECTION_NAME}'...")
    target_collection_ref = db.collection(TARGET_RAG_COLLECTION_NAME)
    batch = db.batch()
    written_count = 0
    for i, chunk_doc in enumerate(chunks_to_write):
        doc_ref = target_collection_ref.document()
        batch.set(doc_ref, chunk_doc)
        written_count +=1
        if (i + 1) % FIRESTORE_BATCH_SIZE == 0: # Commit batch
            batch.commit()
            logger.info(f"Committed batch write, {written_count}/{len(chunks_to_write)} chunks written.")
            batch = db.batch()

    if written_count % FIRESTORE_BATCH_SIZE != 0 : # Commit any remaining writes
        batch.commit()
    logger.info(f"Finished batch write. Total {written_count} chunks written to '{TARGET_RAG_COLLECTION_NAME}'.")


def process_user_data(uid: str):
    logger.info(f"Starting RAG data preparation for UID: {uid}")
    delete_existing_chunks(uid)

    text_splitter = MarkdownTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    all_chunk_docs_to_write: List[Dict[str, Any]] = []

    logger.info(f"Processing Reports for UID: {uid}")
    reports = get_all_reports(uid)
    if not reports:
        logger.info(f"No reports found for UID: {uid}")
    else:
        for report in reports:
            report_id = report.get("id", f"unknown_report_id_{len(all_chunk_docs_to_write)}")
            title = report.get("title", "")
            content = report.get("content", "")
            logger.info(f"  Processing Report ID: {report_id}, Title: '{title[:50]}...'")

            markdown_content = f"# {title}\n\n{content}" if title else content
            if not content.strip() and not title.strip():
                logger.warning(f"  Report ID: {report_id} has no title or content. Skipping.")
                continue

            metadata = {
                "original_uid": uid, "original_doc_type": "report", "original_doc_id": report_id,
                "title": title, "created_at": report.get("created_at"), "updated_at": report.get("updated_at")
            }
            report_chunks = prepare_and_embed_chunks(markdown_content, text_splitter, metadata)
            all_chunk_docs_to_write.extend(report_chunks)
            logger.debug(f"    Generated {len(report_chunks)} chunks for Report ID: {report_id}")

    logger.info(f"Processing Procedures for UID: {uid}")
    procedures = get_all_procedures(uid)
    if not procedures:
        logger.info(f"No procedures found for UID: {uid}")
    else:
        for procedure in procedures:
            task_name = procedure.get("task_name", f"unknown_proc_id_{len(all_chunk_docs_to_write)}")
            content = procedure.get("content", "")
            logger.info(f"  Processing Procedure Task Name: {task_name[:50]}...")

            markdown_content = f"# {task_name}\n\n{content}"
            if not content.strip():
                logger.warning(f"  Procedure Task Name: {task_name} has no content. Skipping.")
                continue

            metadata = {
                "original_uid": uid, "original_doc_type": "procedure", "original_doc_id": task_name,
                "title": task_name, "created_at": procedure.get("created_at"), "updated_at": procedure.get("updated_at")
            }
            procedure_chunks = prepare_and_embed_chunks(markdown_content, text_splitter, metadata)
            all_chunk_docs_to_write.extend(procedure_chunks)
            logger.debug(f"    Generated {len(procedure_chunks)} chunks for Procedure: {task_name}")

    if all_chunk_docs_to_write:
        batch_write_to_firestore(all_chunk_docs_to_write)
    else:
        logger.info(f"No new chunks generated for UID: {uid}. Nothing to write to Firestore.")

    logger.info(f"Finished RAG data preparation for UID: {uid}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare RAG data from Firestore Reports and Procedures for a specific user.")
    parser.add_argument("uid", type=str, help="User ID to process data for.")
    args = parser.parse_args()

    logger.info(f"Script execution started for UID: {args.uid}")
    try:
        process_user_data(args.uid)
        logger.info(f"Script execution completed successfully for UID: {args.uid}")
    except Exception as e:
        logger.error(f"An error occurred during script execution for UID {args.uid}: {e}", exc_info=True)
        sys.exit(1)
