import uuid
from app.core.logging import logger
from app.db.session import SessionLocal
from app.services.pipeline_service import DocumentPipelineService
from app.workers.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def process_document_task(self, document_id_str: str):
    """Celery background worker task for document processing."""
    doc_uuid = uuid.UUID(document_id_str)
    db = SessionLocal()
    try:
        logger.info(f"Celery task received for Document UUID: {doc_uuid}")
        pipeline = DocumentPipelineService()
        pipeline.run_pipeline(doc_uuid, db)
        return {"status": "SUCCESS", "document_id": str(doc_uuid)}
    except Exception as exc:
        logger.error(f"Celery task error processing document {doc_uuid}: {str(exc)}")
        raise self.retry(exc=exc)
    finally:
        db.close()
