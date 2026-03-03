# -*- coding: utf-8 -*-
"""
Finanzberatung Celery tasks.

All tasks use @shared_task to avoid circular imports with the app factory.
Tasks are automatically discovered when celery_worker.py creates the Flask app.

Pipeline: extract → classify → [embed, extract_fields] (parallel) → update_completeness
"""
import logging
from celery import shared_task, chain, group

logger = logging.getLogger(__name__)


@shared_task(ignore_result=False)
def health_check_task():
    """Simple test task to verify Celery worker connectivity."""
    logger.info("Celery health check task executed successfully")
    return {"status": "ok", "message": "Celery worker is running"}


# ---------------------------------------------------------------------------
# Document Pipeline Tasks
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def extract_document_task(self, document_id: int):
    """
    Extract text from an uploaded document (PDF or image).

    Status: UPLOADED → EXTRACTING → EXTRACTED (or ERROR)
    """
    from app.services.finanz_extraction_service import FinanzExtractionService

    logger.info("Starting extraction for document %s", document_id)
    try:
        service = FinanzExtractionService()
        result = service.extract_document(document_id)
        _publish_status(document_id, 'extracted', result.get('page_count', 0))
        return {"document_id": document_id, "status": "extracted", **result}
    except Exception as exc:
        logger.error("Extraction task failed for doc %s: %s", document_id, exc, exc_info=True)
        _publish_status(document_id, 'error', str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def classify_document_task(self, prev_result, document_id: int = None):
    """
    Classify a document's contract type.

    Status: EXTRACTED → CLASSIFYING → CLASSIFIED (or ERROR)
    """
    from app.services.finanz_classification_service import FinanzClassificationService

    doc_id = document_id or (prev_result.get("document_id") if isinstance(prev_result, dict) else None)
    if not doc_id:
        raise ValueError("No document_id provided")

    logger.info("Starting classification for document %s", doc_id)
    try:
        service = FinanzClassificationService()
        result = service.classify_document(doc_id)
        _publish_status(doc_id, 'classified', result.get('type_label', ''))
        return {"document_id": doc_id, "status": "classified", **result}
    except Exception as exc:
        logger.error("Classification task failed for doc %s: %s", doc_id, exc, exc_info=True)
        _publish_status(doc_id, 'error', str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def extract_fields_task(self, prev_result, document_id: int = None):
    """
    Extract structured fields from a classified document.

    Status: CLASSIFIED → ANALYZING → ANALYZED (or ERROR)
    """
    from app.services.finanz_field_extraction_service import FinanzFieldExtractionService

    doc_id = document_id or (prev_result.get("document_id") if isinstance(prev_result, dict) else None)
    if not doc_id:
        raise ValueError("No document_id provided")

    logger.info("Starting field extraction for document %s", doc_id)
    try:
        service = FinanzFieldExtractionService()
        results = service.extract_fields(doc_id)
        _publish_status(doc_id, 'analyzed', len(results))
        return {"document_id": doc_id, "status": "analyzed", "field_count": len(results)}
    except Exception as exc:
        logger.error("Field extraction task failed for doc %s: %s", doc_id, exc, exc_info=True)
        _publish_status(doc_id, 'error', str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=1, default_retry_delay=30)
def embed_document_task(self, prev_result, document_id: int = None):
    """
    Embed document text for similarity search.

    Non-critical — failure doesn't block the pipeline.
    """
    from app.services.finanz_embedding_service import FinanzEmbeddingService

    doc_id = document_id or (prev_result.get("document_id") if isinstance(prev_result, dict) else None)
    if not doc_id:
        raise ValueError("No document_id provided")

    logger.info("Starting embedding for document %s", doc_id)
    try:
        service = FinanzEmbeddingService()
        result = service.embed_document(doc_id)
        return {"document_id": doc_id, "status": "embedded", **result}
    except Exception as exc:
        logger.warning("Embedding task failed for doc %s (non-critical): %s", doc_id, exc)
        return {"document_id": doc_id, "status": "embedding_skipped", "error": str(exc)}


@shared_task
def update_session_completeness(results, session_id: int):
    """
    Update session completeness after pipeline finishes.
    Publishes SSE event with overall progress.
    """
    logger.info("Updating completeness for session %s", session_id)
    try:
        _publish_session_event(session_id, 'pipeline_complete', {
            'results': results if isinstance(results, list) else [results],
        })
    except Exception as e:
        logger.error("Completeness update error for session %s: %s", session_id, e)
    return {"session_id": session_id, "status": "complete"}


# ---------------------------------------------------------------------------
# Pipeline Orchestration
# ---------------------------------------------------------------------------

def process_document_pipeline(document_id: int, session_id: int):
    """
    Launch the full document processing pipeline as a Celery chain.

    Pipeline: extract → classify → [embed, extract_fields] → update_completeness
    """
    pipeline = chain(
        extract_document_task.s(document_id),
        classify_document_task.s(document_id=document_id),
        # After classification, run embedding and field extraction in parallel
        group(
            embed_document_task.s(document_id=document_id),
            extract_fields_task.s(document_id=document_id),
        ),
        update_session_completeness.s(session_id=session_id),
    )

    result = pipeline.apply_async()
    logger.info(
        "Pipeline started for document %s (session %s), task_id=%s",
        document_id, session_id, result.id,
    )
    return result


@shared_task
def generate_scorecard_task(session_id: int):
    """Generate scorecards for a session after all documents are analyzed."""
    from app.services.finanz_scorecard_service import FinanzScorecardService

    logger.info("Generating scorecards for session %s", session_id)
    try:
        service = FinanzScorecardService()
        results = service.generate_scorecard(session_id)
        _publish_session_event(session_id, 'scorecard_generated', {
            'count': len(results),
        })
        return {"session_id": session_id, "scorecard_count": len(results)}
    except Exception as e:
        logger.error("Scorecard generation failed for session %s: %s", session_id, e, exc_info=True)
        raise


# ---------------------------------------------------------------------------
# SSE Helpers
# ---------------------------------------------------------------------------

def _publish_status(document_id: int, status: str, detail=None):
    """Publish document status change via SSE."""
    try:
        from app.models import get_db_session
        from app.models.finanzberatung import FinanzDocument

        db = get_db_session()
        try:
            doc = db.query(FinanzDocument).filter(
                FinanzDocument.id == document_id
            ).first()
            if doc:
                _publish_session_event(doc.session_id, 'document_status', {
                    'document_id': document_id,
                    'status': status,
                    'detail': detail,
                    'filename': doc.original_filename,
                })
        finally:
            db.close()
    except Exception as e:
        logger.debug("SSE publish failed (non-critical): %s", e)


def _publish_session_event(session_id: int, event_type: str, data: dict):
    """Publish an event to the session's SSE channel."""
    try:
        from app.services.finanz_sse_service import sse_manager
        sse_manager.publish(session_id, event_type, data)
    except Exception as e:
        logger.debug("SSE publish failed (non-critical): %s", e)
