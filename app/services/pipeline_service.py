import os
import uuid
from typing import Dict, List
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.db.models.answer_key import AnswerKey
from app.db.models.document import Document
from app.db.models.option import QuestionOption
from app.db.models.page import DocumentPage
from app.db.models.question import Question
from app.db.models.relationship import DocumentRelationship
from app.db.models.review_item import ReviewItem
from app.db.models.source import QuestionSource
from app.schemas.page import PageContent
from app.services.answer_service import AnswerService
from app.services.confidence_service import ConfidenceService
from app.services.pdf_service import PageExtractionService
from app.services.storage_service import LocalStorageService, StorageService
from app.services.universal_parser import UniversalQuestionParser, RawQuestionCandidate, OptionCandidate
from app.services.visual_extractor import VisualExtractorService
from app.services.ai_service import AIService


class DocumentPipelineService:
    """Master pipeline orchestrator that processes documents from raw file to structured questions using the 10-stage universal extraction engine."""

    def __init__(
        self,
        storage_service: StorageService = None,
        page_extractor: PageExtractionService = None,
        ai_service: AIService = None,
    ):
        self.storage_service = storage_service or LocalStorageService()
        self.page_extractor = page_extractor or PageExtractionService()
        self.ai_service = ai_service or AIService()


    def run_pipeline(self, document_id: uuid.UUID, db: Session) -> Document:
        """Executes the complete universal layout-agnostic processing pipeline."""
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found.")

        try:
            logger.info(f"--- Pipeline START: Document {document.id} ({document.filename}) ---")

            # Idempotent cleanup if previously processed
            db.query(ReviewItem).filter(ReviewItem.document_id == document.id).delete()
            db.query(AnswerKey).filter(AnswerKey.document_id == document.id).delete()
            db.query(Question).filter(Question.document_id == document.id).delete()
            db.query(DocumentPage).filter(DocumentPage.document_id == document.id).delete()
            db.commit()

            document.processing_status = "PROCESSING"
            document.processing_stage = "OCR_PROCESSING"
            db.commit()

            # 1. Retrieve physical file
            file_path = self.storage_service.get_file_path(document.stored_filename)

            # 2. Page & Layout Extraction
            pages_content: List[PageContent] = self.page_extractor.process_document_to_pages(
                file_path=file_path,
                document_id=document.id,
                mime_type=document.mime_type,
            )

            # Save pages to DB
            pages_by_num: Dict[int, PageContent] = {}
            dict_pages: List[Dict] = []
            for p in pages_content:
                pages_by_num[p.page_number] = p
                dict_pages.append({
                    "page_number": p.page_number,
                    "raw_text": p.extracted_text,
                })
                page_record = DocumentPage(
                    document_id=document.id,
                    page_number=p.page_number,
                    extracted_text=p.extracted_text,
                    ocr_used=p.ocr_used,
                    ocr_confidence=p.ocr_confidence,
                    image_path=p.image_path,
                    rotation=p.rotation,
                    page_metadata=p.page_metadata,
                )
                db.add(page_record)

            document.page_count = len(pages_content)
            document.processing_stage = "QUESTION_EXTRACTION"
            db.commit()

            # 3. Universal Question Parsing (Candidate Detection, Region Filtering, Horizontal & Multi-line Options)
            candidates: List[RawQuestionCandidate] = UniversalQuestionParser.parse_document_pages(dict_pages)
            logger.info(f"Doc {document.id}: Extracted {len(candidates)} candidate questions.")

            # AI-Assisted Extraction fallback when configured
            if self.ai_service.is_configured() and len(candidates) == 0:
                logger.info(f"Doc {document.id}: Calling AI Service ({self.ai_service.provider}) for assisted question extraction...")
                for p in pages_content:
                    ai_res = self.ai_service.extract_structured_questions(p.extracted_text)
                    if ai_res and ai_res.questions:
                        for ai_q in ai_res.questions:
                            q_opts = [
                                OptionCandidate(key=o.key, text=o.text, order_index=idx+1)
                                for idx, o in enumerate(ai_q.options)
                            ]
                            candidates.append(
                                RawQuestionCandidate(
                                    question_number=ai_q.question_number,
                                    question_text=ai_q.question_text,
                                    question_type=ai_q.question_type,
                                    options=q_opts,
                                    matched_answer=ai_q.matched_answer,
                                    source_pages=[p.page_number],
                                    confidence=0.92
                                )
                            )


            # 4. Visual & Table Extraction (Diagrams, Charts, Circuit Images)
            output_img_dir = os.path.join(os.path.dirname(file_path), "extracted_images")
            candidates = VisualExtractorService.extract_visuals_for_questions(
                doc_path=file_path,
                candidates=candidates,
                output_dir=output_img_dir
            )

            # 5. Answer Key Isolation & Resolution
            document.processing_stage = "ANSWER_MATCHING"
            db.commit()

            answer_blocks = AnswerService.extract_answer_keys_from_pages(pages_content)
            combined_answers: Dict[str, str] = {}

            for page_num, raw_text, ans_map in answer_blocks:
                combined_answers.update(ans_map)
                ak_record = AnswerKey(
                    document_id=document.id,
                    raw_key_text=raw_text,
                    parsed_answers=ans_map,
                    page_number=page_num,
                )
                db.add(ak_record)

            # External Answer Keys
            related_keys = (
                db.query(DocumentRelationship)
                .filter(
                    DocumentRelationship.source_document_id == document.id,
                    DocumentRelationship.relationship_type == "ANSWER_KEY",
                )
                .all()
            )
            for rel in related_keys:
                ext_doc = db.query(Document).filter(Document.id == rel.related_document_id).first()
                if ext_doc:
                    for ext_ak in ext_doc.answer_keys:
                        if ext_ak.parsed_answers:
                            combined_answers.update(ext_ak.parsed_answers)

            # Match answers to candidates
            for cand in candidates:
                if cand.question_number and str(cand.question_number) in combined_answers:
                    cand.matched_answer = combined_answers[str(cand.question_number)]
                    cand.answer_source = "INTERNAL_KEY"

            # 6. Quality Gates, Empirical Confidence Scoring & Review Generator
            document.processing_stage = "VALIDATION"
            db.commit()

            confidence_scores = []
            for cand in candidates:
                conf_score, status_str, review_req, warnings, review_items_data = ConfidenceService.evaluate_candidate(
                    document_id=document.id,
                    candidate=cand,
                    pages_by_number=pages_by_num,
                )
                confidence_scores.append(conf_score)

                first_img_url = cand.images[0]["path"] if cand.images else None

                # Persist Question
                q_model = Question(
                    document_id=document.id,
                    question_number=cand.question_number,
                    question_text=cand.question_text,
                    question_type=cand.question_type,
                    confidence_score=conf_score,
                    extraction_status=status_str,
                    matched_answer=getattr(cand, "matched_answer", None),
                    answer_source=getattr(cand, "answer_source", None),
                    image_url=first_img_url,
                )

                db.add(q_model)
                db.flush()  # Obtain q_model.id

                # Persist Options
                for opt in cand.options:
                    opt_model = QuestionOption(
                        question_id=q_model.id,
                        option_key=opt.key,
                        option_text=opt.text,
                        is_correct=(opt.key == getattr(cand, "matched_answer", None)),
                        order_index=opt.order_index,
                    )
                    db.add(opt_model)

                # Persist Sources
                for src_page in cand.source_pages:
                    src_model = QuestionSource(
                        question_id=q_model.id,
                        page_number=src_page,
                    )
                    db.add(src_model)

                # Persist Review Items
                for r_item in review_items_data:
                    rev_model = ReviewItem(
                        document_id=document.id,
                        question_id=q_model.id,
                        review_type=r_item["review_type"],
                        severity=r_item["severity"],
                        message=r_item["message"],
                        confidence=r_item.get("confidence"),
                        is_resolved=False,
                    )
                    db.add(rev_model)

            # Overall Confidence Calculation
            overall_conf = (
                round(sum(confidence_scores) / len(confidence_scores), 2)
                if confidence_scores
                else 1.0
            )
            document.overall_confidence = overall_conf

            # Determine final status
            has_reviews = any(c < 0.85 for c in confidence_scores)
            if has_reviews and overall_conf < 0.60:
                document.processing_status = "PARTIAL"
            else:
                document.processing_status = "COMPLETED"

            document.processing_stage = "COMPLETED"
            db.commit()
            db.refresh(document)

            logger.info(f"--- Pipeline FINISHED: Doc {document.id} status={document.processing_status} conf={document.overall_confidence} ---")
            return document

        except Exception as e:
            logger.error(f"Pipeline failure on Doc {document.id}: {str(e)}", exc_info=True)
            document.processing_status = "FAILED"
            document.error_message = str(e)
            db.commit()
            raise e
