import re
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel
from app.services.region_classifier import RegionClassifier, RegionType


class OptionCandidate(BaseModel):
    key: str
    text: str
    order_index: int


class RawQuestionCandidate(BaseModel):
    question_number: Optional[str] = None
    question_text: str
    question_type: str = "UNKNOWN"
    context: Optional[str] = None
    context_type: Optional[str] = None
    options: List[OptionCandidate] = []
    matched_answer: Optional[str] = None
    answer_source: Optional[str] = None
    source_pages: List[int] = []
    requires_visual_context: bool = False
    tables: List[Dict[str, Any]] = []
    images: List[Dict[str, Any]] = []
    confidence: float = 0.8
    warnings: List[str] = []


class UniversalQuestionParser:
    """
    Universal layout-agnostic question extraction parser.
    Uses multi-signal question identification (numbering, linguistic cues, options, punctuation).
    Handles inline question separation (Q17, Q18...), horizontal & vertical option extraction,
    and diagram/image context preservation.
    """

    NUMBERED_QUESTION_PATTERNS = [
        r"^\s*Q(?:uestion|ue)?\.?\s*(?:No\.?)?\s*(\d+)\s*[\.\)\:\-]?\s*(.*)",
        r"^\s*Question\s+(\d+)\s*[\.\)\:\-]?\s*(.*)",
        r"^\s*(\d{1,3})\s*[\.\)]\s+(.*)",
    ]

    LINGUISTIC_PROMPTS = [
        "which of the following",
        "calculate the",
        "find the",
        "determine the",
        "consider the following",
        "match the following",
        "select the correct",
        "what is the",
        "how many",
        "explain the",
        "discuss the",
        "write a program",
        "write a function",
        "read the following passage",
        "assertion (a):",
        "statement i:",
        "given below are two statement",
        "given below are two statements",
    ]

    HEADER_PREFIXES = [
        r"^\s*(?:NEET|JEE|GATE|CAT|UPSC|CBSE|PHYSICS|CHEMISTRY|BIOLOGY|BOTANY|ZOOLOGY|MATHEMATICS)\s+",
        r"^\s*(?:SECTION|PART|GROUP)\s+[-–—\s]*[A-Z0-9]+\s+",
    ]

    @classmethod
    def clean_leading_headers(cls, text: str) -> str:
        clean = text.strip()
        for pat in cls.HEADER_PREFIXES:
            clean = re.sub(pat, "", clean, flags=re.IGNORECASE).strip()
        return clean

    @classmethod
    def is_question_start(cls, line: str) -> Tuple[bool, Optional[str], Optional[str]]:
        clean = line.strip()
        if not clean or RegionClassifier.is_non_question_content(clean):
            return False, None, None

        if RegionClassifier.is_imperative_command(clean):
            return False, None, None

        clean_stem = cls.clean_leading_headers(clean)

        for pat in cls.NUMBERED_QUESTION_PATTERNS:
            match = re.match(pat, clean_stem, re.IGNORECASE)
            if match:
                q_num = match.group(1)
                rem_text = match.group(2).strip()

                if re.match(r"^[A-D1-4]$", rem_text, re.IGNORECASE):
                    return False, None, None

                if rem_text and (RegionClassifier.is_non_question_content(rem_text) or RegionClassifier.is_imperative_command(rem_text)):
                    return False, None, None

                return True, q_num, rem_text

        lower = clean_stem.lower()
        for prompt in cls.LINGUISTIC_PROMPTS:
            if lower.startswith(prompt):
                return True, None, clean_stem

        return False, None, None

    @classmethod
    def parse_horizontal_options(cls, text: str) -> List[OptionCandidate]:
        options = []
        patterns = [
            r"(?:^|\s{2,})([\(]?[A-Da-d][\)\.]|[A-D]\.)\s+(.*?)(?=(?:\s{2,}[\(]?[A-Da-d][\)\.]|\b[A-D]\.)\s+|$)",
            r"(?:^|\s{2,})([\(]?[1-4][\)\.]|[1-4]\.)\s+(.*?)(?=(?:\s{2,}[\(]?[1-4][\)\.]|[1-4]\.)\s+|$)",
            r"(?:^|\s{2,})([1-4])\s+(.*?)(?=(?:\s{2,}[1-4])\s+|$)",
            r"(?:^|\s+)([\(][1-4][\)])\s+(.*?)(?=(?:\s+[\(][1-4][\)])\s+|$)",
        ]

        for pat in patterns:
            matches = list(re.finditer(pat, text))
            if len(matches) >= 2:
                idx = 1
                for m in matches:
                    raw_key = m.group(1).strip("().")
                    opt_text = m.group(2).strip()
                    options.append(OptionCandidate(key=raw_key.upper(), text=opt_text, order_index=idx))
                    idx += 1
                break

        return options

    @classmethod
    def classify_question_type(cls, question_text: str, options: List[OptionCandidate]) -> str:
        lower = question_text.lower()

        if "assertion (a)" in lower or "assertion a" in lower or "given below are two statement" in lower:
            return "ASSERTION_REASON"
        if "match the following" in lower or "column i" in lower:
            return "MATCH_THE_FOLLOWING"
        if "read the following passage" in lower or "passage:" in lower:
            return "PASSAGE_BASED"
        if "write a program" in lower or "write a function" in lower or "def " in lower or "public class" in lower:
            return "CODING"
        if "______" in question_text or "fill in the blank" in lower:
            return "FILL_IN_THE_BLANK"

        if options:
            opt_texts = [o.text.lower().strip() for o in options]
            if len(options) == 2 and set(opt_texts) == {"true", "false"}:
                return "TRUE_FALSE"
            return "MCQ"

        if "explain" in lower or "discuss" in lower or "describe" in lower:
            return "DESCRIPTIVE"
        if "calculate" in lower or "find" in lower or "determine" in lower:
            return "NUMERICAL"

        return "UNKNOWN"

    @classmethod
    def parse_document_pages(cls, pages: List[Dict[str, Any]]) -> List[RawQuestionCandidate]:
        candidates: List[RawQuestionCandidate] = []
        current_passage: Optional[str] = None
        in_answer_key_section = False

        current_candidate: Optional[RawQuestionCandidate] = None
        current_option: Optional[OptionCandidate] = None

        for page in pages:
            page_num = page.get("page_number", 1)
            raw_text = page.get("raw_text", "")

            # Universal inline question separator: splits Q17, Q18, Question 19 onto separate lines
            normalized_text = re.sub(r"(\s+)(Q\s*\d+\b)", r"\n\2 ", raw_text, flags=re.IGNORECASE)
            normalized_text = re.sub(r"(\s+)(Question\s+\d+\b)", r"\n\2 ", normalized_text, flags=re.IGNORECASE)
            lines = normalized_text.split("\n")

            for line in lines:
                clean = line.strip()
                if not clean:
                    continue

                region, _ = RegionClassifier.classify_line(clean, page_num)

                if region == RegionType.ANSWER_KEY or clean.lower().startswith("answer key"):
                    in_answer_key_section = True
                    if current_candidate:
                        current_candidate.question_type = cls.classify_question_type(
                            current_candidate.question_text, current_candidate.options
                        )
                        if not RegionClassifier.is_imperative_command(current_candidate.question_text):
                            candidates.append(current_candidate)
                        current_candidate = None
                    continue

                if in_answer_key_section:
                    continue

                if region in [RegionType.INSTRUCTION, RegionType.HEADER, RegionType.FOOTER, RegionType.METADATA, RegionType.CANDIDATE_FIELD]:
                    continue

                if region == RegionType.PASSAGE or clean.lower().startswith("read the following passage"):
                    current_passage = clean
                    continue

                is_start, q_num, rem_text = cls.is_question_start(clean)

                # If current candidate has no question text yet (e.g. Q1 was on previous line)
                # and this line has NO new question number, this line belongs to current_candidate
                if current_candidate and not current_candidate.question_text.strip() and not q_num:
                    clean_text = rem_text if rem_text else clean
                    clean_text = cls.clean_leading_headers(clean_text)
                    current_candidate.question_text = clean_text
                    horiz_opts = cls.parse_horizontal_options(clean_text)
                    if horiz_opts:
                        stem_text = re.split(r"(?:^|\s+)([\(]?[A-Da-d1-4][\)\.]|\b[A-D1-4]\b[\.\)]?)\s+", clean_text)[0].strip()
                        current_candidate.question_text = stem_text
                        current_candidate.options = horiz_opts
                    continue

                if is_start:
                    if current_candidate and current_candidate.question_text.strip():
                        current_candidate.question_type = cls.classify_question_type(
                            current_candidate.question_text, current_candidate.options
                        )
                        if not RegionClassifier.is_imperative_command(current_candidate.question_text):
                            candidates.append(current_candidate)

                    rem_text = cls.clean_leading_headers(rem_text or "")

                    current_candidate = RawQuestionCandidate(
                        question_number=q_num,
                        question_text=rem_text or "",
                        context=current_passage,
                        context_type="PASSAGE" if current_passage else None,
                        source_pages=[page_num],
                        options=[]
                    )
                    current_option = None

                    if rem_text:
                        horiz_opts = cls.parse_horizontal_options(rem_text)
                        if horiz_opts:
                            stem_text = re.split(r"(?:^|\s+)([\(]?[A-Da-d1-4][\)\.]|\b[A-D1-4]\b[\.\)]?)\s+", rem_text)[0].strip()
                            current_candidate.question_text = stem_text
                            current_candidate.options = horiz_opts
                    continue

                if current_candidate:
                    if page_num not in current_candidate.source_pages:
                        current_candidate.source_pages.append(page_num)

                    horiz_opts = cls.parse_horizontal_options(clean)
                    if horiz_opts:
                        current_candidate.options.extend(horiz_opts)
                        current_option = current_candidate.options[-1]
                        continue

                    opt_match = re.match(r"^\s*([\(]?[A-Da-d1-4i-v][\)\.]?|[A-D1-4][\.\)]?)\s+(.*)", clean)
                    if opt_match:
                        opt_key = opt_match.group(1).strip("().").upper()
                        opt_val = opt_match.group(2).strip()

                        idx = len(current_candidate.options) + 1
                        current_option = OptionCandidate(key=opt_key, text=opt_val, order_index=idx)
                        current_candidate.options.append(current_option)
                        continue

                    if current_option and current_candidate.options:
                        current_option.text += " " + clean
                        current_candidate.options[-1] = current_option
                        continue

                    if not current_candidate.options:
                        current_candidate.question_text += " " + clean

        if current_candidate:
            current_candidate.question_type = cls.classify_question_type(
                current_candidate.question_text, current_candidate.options
            )
            if not RegionClassifier.is_imperative_command(current_candidate.question_text):
                candidates.append(current_candidate)

        return candidates
