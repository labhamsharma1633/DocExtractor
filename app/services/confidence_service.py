import uuid
from typing import Dict, List, Optional, Tuple, Any
from app.db.models.review_item import ReviewItem
from app.schemas.page import PageContent


class ConfidenceService:
    """Calculates explainable confidence scores and produces granular review items."""

    @classmethod
    def evaluate_candidate(
        cls,
        document_id: uuid.UUID,
        candidate: Any,
        pages_by_number: Dict[int, PageContent],
    ) -> Tuple[float, str, bool, List[str], List[Dict]]:
        """
        Calculates empirical confidence score (0.0 - 1.0), extraction status, review_required flag,
        warnings, and detailed review items.
        """
        score = 0.0
        warnings: List[str] = []
        review_items: List[Dict] = []
        review_required = False

        q_text = getattr(candidate, "question_text", "") or ""
        q_num = getattr(candidate, "question_number", None)
        q_type = getattr(candidate, "question_type", "UNKNOWN")
        options = getattr(candidate, "options", []) or []
        matched_ans = getattr(candidate, "matched_answer", None)
        source_pages = getattr(candidate, "source_pages", [1]) or [1]
        requires_visual = getattr(candidate, "requires_visual_context", False)
        images = getattr(candidate, "images", []) or []

        # 1. Question Text Presence (+0.30)
        if len(q_text) >= 10:
            score += 0.30
        elif len(q_text) > 0:
            score += 0.15
            warnings.append("Question text appears unusually short.")
            review_items.append({
                "review_type": "UNCLEAR_QUESTION_TEXT",
                "severity": "HIGH",
                "message": "Question text appears truncated or unusually short.",
                "confidence": 0.40,
            })
        else:
            review_required = True
            warnings.append("Question text is missing.")
            review_items.append({
                "review_type": "MISSING_QUESTION_TEXT",
                "severity": "CRITICAL",
                "message": "Question text is missing.",
                "confidence": 0.10,
            })

        # 2. Question Numbering Signal (+0.20)
        if q_num is not None:
            score += 0.20
        else:
            warnings.append("Question does not have an explicit number.")
            review_items.append({
                "review_type": "MISSING_QUESTION_NUMBER",
                "severity": "MEDIUM",
                "message": "Question could not be assigned a number from the document.",
                "confidence": 0.50,
            })

        # 3. Option Structure & Type Signal (+0.25)
        if q_type in ["MCQ", "SINGLE_CHOICE", "MULTIPLE_CHOICE"]:
            if len(options) >= 4:
                score += 0.25
            elif len(options) >= 2:
                score += 0.15
                warnings.append(f"MCQ has only {len(options)} options.")
                review_items.append({
                    "review_type": "FEW_OPTIONS",
                    "severity": "MEDIUM",
                    "message": f"MCQ has only {len(options)} options extracted.",
                    "confidence": 0.70,
                })
            else:
                review_required = True
                warnings.append("MCQ is missing options.")
                review_items.append({
                    "review_type": "MISSING_OPTIONS",
                    "severity": "HIGH",
                    "message": "Multiple-choice question options could not be extracted.",
                    "confidence": 0.35,
                })
        elif q_type in ["TRUE_FALSE", "SHORT_ANSWER", "DESCRIPTIVE", "FILL_IN_THE_BLANK", "NUMERICAL", "CODING", "ASSERTION_REASON", "MATCH_THE_FOLLOWING", "PASSAGE_BASED"]:
            score += 0.25
        else:
            score += 0.10
            warnings.append("Uncertain question type.")
            review_items.append({
                "review_type": "UNSUPPORTED_STRUCTURE",
                "severity": "LOW",
                "message": "Question structure is ambiguous or unclassified.",
                "confidence": 0.50,
            })

        # 4. Source Page & OCR Signal (+0.15)
        ocr_confs = []
        for p_num in source_pages:
            p_obj = pages_by_number.get(p_num)
            if p_obj and p_obj.ocr_used and p_obj.ocr_confidence is not None:
                ocr_confs.append(p_obj.ocr_confidence)

        if not ocr_confs:
            score += 0.15
        else:
            avg_ocr = sum(ocr_confs) / len(ocr_confs)
            if avg_ocr >= 80.0:
                score += 0.15
            elif avg_ocr >= 60.0:
                score += 0.10
            else:
                score += 0.05
                warnings.append(f"Low OCR confidence ({round(avg_ocr, 1)}%).")
                review_items.append({
                    "review_type": "OCR_UNCERTAINTY",
                    "severity": "MEDIUM",
                    "message": f"OCR average confidence is low ({round(avg_ocr, 1)}%).",
                    "confidence": round(avg_ocr / 100.0, 2),
                })

        # 5. Answer Key Match Signal (+0.10)
        if matched_ans:
            score += 0.10

        # 6. Visual context requirement check
        if requires_visual and not images:
            review_required = True
            warnings.append("Visual diagram/image is essential but missing.")
            review_items.append({
                "review_type": "MISSING_VISUAL_CONTEXT",
                "severity": "HIGH",
                "message": "Visual context (diagram/image) is required for this question.",
                "confidence": 0.40,
            })

        final_score = round(min(max(score, 0.0), 1.0), 2)

        if review_required or final_score < 0.60:
            status_str = "REVIEW"
            review_required = True
        elif final_score < 0.85:
            status_str = "PARTIAL"
        else:
            status_str = "EXTRACTED"

        return final_score, status_str, review_required, warnings, review_items

    @classmethod
    def evaluate_question(
        cls,
        document_id: uuid.UUID,
        question: Any,
        pages_by_number: Dict[int, PageContent],
    ) -> Tuple[float, str, List[Dict]]:
        score, status, _, _, items = cls.evaluate_candidate(document_id, question, pages_by_number)
        return score, status, items

