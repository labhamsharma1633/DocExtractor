import re
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel


class RegionType(str, Enum):
    DOCUMENT_TITLE = "DOCUMENT_TITLE"
    INSTRUCTION = "INSTRUCTION"
    HEADER = "HEADER"
    FOOTER = "FOOTER"
    SECTION_HEADER = "SECTION_HEADER"
    SUBJECT_HEADER = "SUBJECT_HEADER"
    CANDIDATE_FIELD = "CANDIDATE_FIELD"
    METADATA = "METADATA"
    QUESTION = "QUESTION"
    OPTION = "OPTION"
    ANSWER_KEY = "ANSWER_KEY"
    ANSWER_KEY_HEADER = "ANSWER_KEY_HEADER"
    PASSAGE = "PASSAGE"
    TABLE = "TABLE"
    IMAGE = "IMAGE"
    OTHER = "OTHER"


class TextRegion(BaseModel):
    id: str
    page_number: int
    text: str
    region_type: RegionType
    confidence: float
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1]
    is_question_candidate: bool = False


class RegionClassifier:
    """
    Universal Semantic Region Classifier.
    Uses layout preambles, structural signals, and imperative command grammar
    to filter out non-question content automatically across ALL exam/coaching PDFs.
    """

    INSTRUCTION_KEYWORDS = [
        "instruction", "instructions", "candidates", "particulars", "test booklet",
        "duration", "maximum marks", "max marks", "total marks", "time allowed",
        "read the following", "do not open", "fill in", "roll number", "registration number",
        "omr sheet", "use blue", "use black", "ball point pen", "negative marking",
        "each question carries", "marks will be deducted", "rough work", "space for rough work",
        "general directions", "important notes", "hall ticket", "signature of candidate",
        "invigilator signature", "prohibited", "electronic devices", "calculator",
        "bubbles", "darken", "pencils", "whiteners", "multiple markings", "invalid responses",
        "rectify filling errors", "filling errors", "tick mark", "over-filled", "half-filled"
    ]

    IMPERATIVE_COMMAND_STARTERS = [
        "darken", "do not", "don't", "never", "ensure", "fill", "use", "candidates",
        "please", "mark", "carry", "bring", "prohibited", "allowed", "submit", "return",
        "verify", "check", "keep", "avoid", "detach", "fold", "tear", "mutilate",
        "sign", "write", "enter", "circle", "shade"
    ]

    HEADER_FOOTER_PATTERNS = [
        r"^\s*page\s+\d+\s+(?:of|\/)\s+\d+\s*$",
        r"^\s*\d+\s+(?:of|\/)\s+\d+\s*$",
        r"^\s*page\s+\d+\s*$",
        r"^\s*copyright\s+.*$",
        r"^\s*all\s+rights\s+reserved.*$",
        r"^\s*set\s+[-–—\s]*[A-Z0-9]+\s*$",
        r"^\s*code\s+[-–—\s]*[A-Z0-9]+\s*$"
    ]

    METADATA_PATTERNS = [
        r"^\s*(?:duration|time\s+allowed|time)\s*:\s*\d+.*$",
        r"^\s*(?:max|maximum)\s+marks\s*:\s*\d+.*$",
        r"^\s*total\s+(?:questions|no\.\s+of\s+questions)\s*:\s*\d+.*$",
        r"^\s*candidate(?:'s)?\s+name\s*:.*$",
        r"^\s*roll\s+no(?:\.|\s)\s*:.*$",
        r"^\s*registration\s+no(?:\.|\s)\s*:.*$",
        r"^\s*booklet\s+code\s*:.*$"
    ]

    SECTION_PATTERNS = [
        r"^\s*(?:section|part|group)\s+[-–—\s]*[A-Z0-9]+\s*$",
        r"^\s*(?:physics|chemistry|biology|mathematics|botany|zoology|general\s+awareness|english|reasoning|aptitude)\s*$",
        r"^\s*(?:section|part)\s+[-–—\s]*[A-Z0-9]+\s*[-–:]\s*.*$"
    ]

    ANSWER_KEY_PATTERNS = [
        r"^\s*answer\s+key\s*$",
        r"^\s*answers\s*$",
        r"^\s*solutions?\s+key\s*$",
        r"^\s*(?:\d+[\.\s\:\-]+[A-D1-4]\s*){3,}$",  # Compact answer key list like 1.A 2.C 3.B
    ]

    @classmethod
    def is_imperative_command(cls, text: str) -> bool:
        clean = text.strip().lower()
        # Remove leading number like "2. " or "Q2 "
        clean_stem = re.sub(r"^\s*(?:Q\d+|\d+)[\.\)\:\-]\s*", "", clean).strip()
        for cmd in cls.IMPERATIVE_COMMAND_STARTERS:
            if clean_stem.startswith(cmd):
                return True
        return False

    @classmethod
    def classify_line(cls, text: str, page_number: int = 1, is_top_or_bottom: bool = False) -> Tuple[RegionType, float]:
        clean = text.strip()
        lower = clean.lower()

        if not clean:
            return RegionType.OTHER, 1.0

        # Check Answer Key Header / Block
        for pat in cls.ANSWER_KEY_PATTERNS:
            if re.search(pat, lower):
                return RegionType.ANSWER_KEY, 0.95

        # Check Header / Footer
        if is_top_or_bottom:
            for pat in cls.HEADER_FOOTER_PATTERNS:
                if re.match(pat, lower):
                    return RegionType.HEADER if is_top_or_bottom else RegionType.FOOTER, 0.95

        # Check Metadata
        for pat in cls.METADATA_PATTERNS:
            if re.match(pat, lower):
                return RegionType.METADATA, 0.95

        # Check Section / Subject Headings
        for pat in cls.SECTION_PATTERNS:
            if re.match(pat, lower):
                return RegionType.SECTION_HEADER, 0.90

        # Check Instructions & Imperative Commands
        if cls.is_imperative_command(clean):
            return RegionType.INSTRUCTION, 0.95

        for kw in cls.INSTRUCTION_KEYWORDS:
            if kw in lower:
                return RegionType.INSTRUCTION, 0.92

        # Check Candidate Fields
        if "name of the candidate" in lower or "signature of candidate" in lower or "roll no." in lower:
            return RegionType.CANDIDATE_FIELD, 0.95

        # Check if line looks like Option
        if re.match(r"^\s*(?:[\(]?[A-Da-d1-4i-v][\)\.]\s+|[A-D]\.\s+)", clean):
            return RegionType.OPTION, 0.85

        # Check for Question / Passage
        if re.match(r"^\s*(?:Q\.?|Question\s*|Que\.?\s*)?\d+[\.\)\:]\s+", clean) or lower.startswith("which of the following") or lower.startswith("calculate") or lower.startswith("find"):
            return RegionType.QUESTION, 0.85

        if lower.startswith("read the following passage") or lower.startswith("passage:"):
            return RegionType.PASSAGE, 0.90

        return RegionType.OTHER, 0.50

    @classmethod
    def is_non_question_content(cls, text: str) -> bool:
        region, _ = cls.classify_line(text, 1)
        return region in [
            RegionType.DOCUMENT_TITLE,
            RegionType.INSTRUCTION,
            RegionType.HEADER,
            RegionType.FOOTER,
            RegionType.SECTION_HEADER,
            RegionType.SUBJECT_HEADER,
            RegionType.CANDIDATE_FIELD,
            RegionType.METADATA,
            RegionType.ANSWER_KEY,
            RegionType.ANSWER_KEY_HEADER,
        ]
