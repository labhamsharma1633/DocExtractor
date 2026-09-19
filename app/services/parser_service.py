import re
from typing import Dict, List, Optional, Tuple


class ParsedOption:
    def __init__(self, key: str, text: str, is_correct: Optional[bool] = None, order_index: int = 0):
        self.key = key.upper()
        self.text = text.strip()
        self.is_correct = is_correct
        self.order_index = order_index

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "text": self.text,
            "is_correct": self.is_correct,
            "order_index": self.order_index,
        }


class ParsedQuestion:
    def __init__(
        self,
        question_number: Optional[str],
        question_text: str,
        options: List[ParsedOption] = None,
        source_pages: List[int] = None,
        question_type: str = "UNKNOWN",
    ):
        self.question_number = question_number
        self.question_text = question_text.strip()
        self.options = options or []
        self.source_pages = source_pages or []
        self.question_type = question_type
        self.matched_answer: Optional[str] = None
        self.answer_source: Optional[str] = None
        self.image_url: Optional[str] = None
        self.confidence_score: float = 1.0
        self.extraction_status: str = "EXTRACTED"
        self.review_warnings: List[str] = []



class QuestionParserService:
    """Deterministic parser that extracts structured questions, options, and types from text lines."""

    # Matches:
    # 1. / 1) / 01. / 01)
    # Q1. / Q1 / Q.1 / Q 1. / Question 1 / Que. 1:
    QUESTION_PATTERN = re.compile(
        r"^(?:(?:Question|Que|Q)\.?\s*(\d+|[ivxlcdm]+)[\.\:\)]?|\b(\d{1,3})[\.\)]|\b(0\d)[\.\)])\s*(.*)$",
        re.IGNORECASE,
    )

    # Option patterns:
    # A. / B. / A) / (A) / (a) / (1) / 1. (in option context)
    OPTION_PATTERN = re.compile(
        r"^\s*(?:\(([a-dA-D1-4])\)|([a-dA-D1-4])[\.\)])\s+(.*)$"
    )

    # Inline option pattern: (A) ... (B) ... (C) ... (D) ... or A. ... B. ...
    INLINE_OPTION_SPLIT = re.compile(
        r"(?:\s+|^)(?:\(([a-dA-D1-4])\)|([a-dA-D1-4])[\.\)])\s+"
    )

    ANSWER_KEY_HEADER = re.compile(
        r"^(?:Answer\s*Key|Answers|Solutions|Key\s*Answers)[\:\s]*$",
        re.IGNORECASE,
    )

    INSTRUCTION_HEADER_PATTERN = re.compile(
        r"^(?:General\s+Instructions|OMR\s+Instructions|Instructions(?:\s+to\s+Candidates)?|Important\s+Instructions|Topics\s+Covered|Rules\s+(?:and|\&|\+)\s+Regulations|Candidate\s+Instructions|Space\s+for\s+Rough\s+Work)[\:\s]*$",
        re.IGNORECASE,
    )

    SECTION_HEADER_PATTERN = re.compile(
        r"^(?:Physics|Chemistry|Botany|Zoology|Biology|Mathematics|Section\s*[\-\:]?\s*[A-Z]|Part\s*[\-\:]?\s*[A-Z])[\:\s]*$",
        re.IGNORECASE,
    )

    EXPLICIT_Q_PATTERN = re.compile(
        r"^(?:(?:Question|Que|Q)\.?\s*(\d+|[ivxlcdm]+)[\.\:\)]?)\s*(.*)$",
        re.IGNORECASE,
    )

    INSTRUCTION_KEYWORDS = [
        "fill in the particulars",
        "test booklet",
        "invigilator",
        "omr sheet",
        "omr bar code",
        "ballpoint pen",
        "white fluid",
        "whiteners",
        "stray mark",
        "examination room",
        "examination hall",
        "no student is allowed",
        "candidate's signature",
        "invigilator's signature",
        "space for rough work",
        "topics covered",
        "roll number",
        "name of the student",
        "maximum marks",
        "mark will be deducted",
        "duration and the test booklet",
        "correct response for each question",
        "darken the bubbles",
        "never use pencils",
        "multiple markings",
        "do not fold or make any stray mark",
        "master ncert with pw",
        "pw web/app",
        "yakeen neet",
        "practice test -",
        "duration :",
        "m. marks :",
        "smart.link",
        "physics wallah",
        "allen career",
        "fiitjee",
        "resonance",
        "aakash institute",
        "test series",
        "mock test paper",
        "question paper code",
        "all questions are compulsory",
        "this test booklet contains",
    ]

    @classmethod
    def is_instruction_text(cls, text: str) -> bool:
        """Returns True if text contains common test instructions/cover page metadata phrases."""
        t_lower = text.lower()
        return any(kw in t_lower for kw in cls.INSTRUCTION_KEYWORDS)

    @classmethod
    def is_question_start(cls, line: str) -> Tuple[bool, Optional[str], str]:
        """Detects if a line starts a new question. Returns (is_match, question_number, remaining_text)."""
        line_clean = line.strip()
        if cls.ANSWER_KEY_HEADER.match(line_clean):
            return False, None, line_clean

        match = cls.QUESTION_PATTERN.match(line_clean)
        if match:
            q_num = match.group(1) or match.group(2) or match.group(3)
            if q_num and q_num.isdigit():
                q_num = str(int(q_num))
            remaining = match.group(4) or ""
            return True, q_num, remaining
        return False, None, line_clean

    @classmethod
    def is_option_line(cls, line: str) -> Tuple[bool, Optional[str], str]:
        """Detects if a line starts an option item. Returns (is_match, option_key, option_text)."""
        line_clean = line.strip()
        match = cls.OPTION_PATTERN.match(line_clean)
        if match:
            key = match.group(1) or match.group(2)
            text = match.group(3) or ""
            return True, key, text
        return False, None, line_clean

    @classmethod
    def extract_inline_options(cls, text: str) -> List[ParsedOption]:
        """Extracts options formatted horizontally on a single line (e.g. A. True B. False)."""
        matches = list(cls.INLINE_OPTION_SPLIT.finditer(text))
        if len(matches) < 2:
            return []

        options: List[ParsedOption] = []
        for idx, m in enumerate(matches):
            key = m.group(1) or m.group(2)
            start_pos = m.end()
            end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            opt_text = text[start_pos:end_pos].strip()
            options.append(ParsedOption(key=key, text=opt_text, order_index=idx))

        return options

    @classmethod
    def classify_type(cls, question_text: str, options: List[ParsedOption]) -> str:
        """Determines question type (MCQ, TRUE_FALSE, SHORT_ANSWER, DESCRIPTIVE, UNKNOWN)."""
        lower_q = question_text.lower()
        if len(options) >= 2:
            opt_texts = [opt.text.lower() for opt in options]
            if set(opt_texts) in [{"true", "false"}, {"yes", "no"}]:
                return "TRUE_FALSE"
            return "MCQ"

        if "true or false" in lower_q or "state true or false" in lower_q:
            return "TRUE_FALSE"
        if any(lower_q.startswith(w) for w in ["explain", "discuss", "describe", "elaborate", "derive", "write a note"]):
            return "DESCRIPTIVE"
        if any(lower_q.startswith(w) for w in ["what is", "define", "name the", "fill in the blank", "which year", "which of"]):
            return "SHORT_ANSWER"

        return "UNKNOWN"
