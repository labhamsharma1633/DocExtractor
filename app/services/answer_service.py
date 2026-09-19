import re
from typing import Dict, List, Optional, Tuple
from app.schemas.page import PageContent
from app.services.parser_service import ParsedQuestion


class AnswerService:
    """Detects and parses answer key blocks and matches answers to questions."""

    # Patterns for answer key headers
    ANSWER_HEADER_PATTERN = re.compile(
        r"^(?:Answer\s*Key|Answers|Solutions|Key\s*Answers)[\:\s]*$",
        re.IGNORECASE,
    )

    # Patterns for answer pairs:
    # 1. A / 1 - B / 1) C / Q1: D / 1. True / 01. B
    ANSWER_PAIR_PATTERN = re.compile(
        r"(?:(?:Q|Question)?[\.\s]*(\d+|[ivxlcdm]+)[\.\:\)\-]?\s*[\:\-\>]?\s*\(?([a-dA-D]|True|False|Yes|No)\)?)",
        re.IGNORECASE,
    )

    @classmethod
    def extract_answer_keys_from_pages(
        cls, pages: List[PageContent]
    ) -> List[Tuple[int, str, Dict[str, str]]]:
        """Scans pages for Answer Key sections and parses question-number -> answer mappings."""
        answer_blocks: List[Tuple[int, str, Dict[str, str]]] = []

        for page in pages:
            lines = page.extracted_text.splitlines()
            is_in_answer_block = False
            current_raw_block: List[str] = []

            for line in lines:
                line_clean = line.strip()
                if not line_clean:
                    continue

                if cls.ANSWER_HEADER_PATTERN.match(line_clean):
                    is_in_answer_block = True
                    current_raw_block.append(line_clean)
                    continue

                if is_in_answer_block:
                    current_raw_block.append(line_clean)

            # If an explicit answer header was found, or if entire page consists of dense answer pairs
            text_to_parse = "\n".join(current_raw_block) if current_raw_block else page.extracted_text
            parsed_dict = cls.parse_answer_pairs(text_to_parse)

            # Only register as an answer key if at least 2 answer pairs are detected
            if len(parsed_dict) >= 2:
                raw_text = text_to_parse
                answer_blocks.append((page.page_number, raw_text, parsed_dict))

        return answer_blocks

    @classmethod
    def parse_answer_pairs(cls, text: str) -> Dict[str, str]:
        """Extracts question number to answer mappings from raw text."""
        answers: Dict[str, str] = {}
        for match in cls.ANSWER_PAIR_PATTERN.finditer(text):
            q_num = match.group(1)
            ans = match.group(2).upper()
            if q_num.isdigit():
                q_num = str(int(q_num))
            answers[q_num] = ans
        return answers

    @classmethod
    def match_answers_to_questions(
        cls,
        questions: List[ParsedQuestion],
        answer_dict: Dict[str, str],
        source_label: str = "INTERNAL_KEY",
    ) -> None:
        """Associates extracted answers with questions and marks correct options."""
        for q in questions:
            if not q.question_number:
                continue

            clean_q_num = q.question_number
            if clean_q_num.isdigit():
                clean_q_num = str(int(clean_q_num))

            if clean_q_num in answer_dict:
                ans_val = answer_dict[clean_q_num]
                q.matched_answer = ans_val
                q.answer_source = source_label

                # Mark corresponding option as correct
                for opt in q.options:
                    if opt.key.upper() == ans_val or opt.text.strip().upper() == ans_val:
                        opt.is_correct = True
                    else:
                        opt.is_correct = False
