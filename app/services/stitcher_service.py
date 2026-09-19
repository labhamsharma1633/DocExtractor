from typing import List
from app.schemas.page import PageContent
from app.services.parser_service import (
    ParsedOption,
    ParsedQuestion,
    QuestionParserService,
)


class MultiPageStitcherService:
    """Processes normalized pages sequentially and stitches questions spanning across page boundaries."""

    @classmethod
    def extract_questions_from_pages(
        cls, pages: List[PageContent]
    ) -> List[ParsedQuestion]:
        """Extracts and stitches all questions from an ordered list of normalized pages."""
        questions: List[ParsedQuestion] = []
        active_question: ParsedQuestion = None
        active_option: ParsedOption = None
        in_answer_key_section = False
        in_instruction_section = False

        # Sort pages by page number to guarantee proper document sequence
        sorted_pages = sorted(pages, key=lambda p: p.page_number)

        for page in sorted_pages:
            lines = [ln.strip() for ln in page.extracted_text.splitlines() if ln.strip()]

            for line in lines:
                # If we encounter an Answer Key header, stop question extraction for this document/section
                if QuestionParserService.ANSWER_KEY_HEADER.match(line):
                    in_answer_key_section = True
                    if active_question:
                        cls._finalize_question(active_question)
                        if cls._is_valid_question(active_question):
                            questions.append(active_question)
                        active_question = None
                        active_option = None
                    break  # Skip rest of this page or section

                if in_answer_key_section:
                    continue

                # Check if line marks an instruction or cover page header
                if QuestionParserService.INSTRUCTION_HEADER_PATTERN.match(line):
                    in_instruction_section = True
                    if active_question:
                        cls._finalize_question(active_question)
                        if cls._is_valid_question(active_question):
                            questions.append(active_question)
                        active_question = None
                        active_option = None
                    continue

                if in_instruction_section:
                    # Instruction section ends when an explicit question header or subject/section header appears
                    if (
                        QuestionParserService.EXPLICIT_Q_PATTERN.match(line)
                        or QuestionParserService.SECTION_HEADER_PATTERN.match(line)
                    ):
                        in_instruction_section = False
                    else:
                        continue

                # Skip direct instruction text or cover page fields
                if QuestionParserService.is_instruction_text(line):
                    continue

                # 1. Check if line starts a new question
                is_q, q_num, q_rem = QuestionParserService.is_question_start(line)
                if is_q:
                    # Ignore if the question text or full line is an instruction
                    if QuestionParserService.is_instruction_text(q_rem) or QuestionParserService.is_instruction_text(line):
                        continue

                    # Finalize previous active question
                    if active_question:
                        cls._finalize_question(active_question)
                        if cls._is_valid_question(active_question):
                            questions.append(active_question)

                    active_question = ParsedQuestion(
                        question_number=q_num,
                        question_text=q_rem,
                        options=[],
                        source_pages=[page.page_number],
                    )
                    active_question.image_url = page.image_path
                    active_option = None
                    continue


                # 2. Check if line is an option (A. / B. / (a) / etc.)
                is_opt, opt_key, opt_rem = QuestionParserService.is_option_line(line)
                if is_opt and active_question:
                    # Check if option continued onto a new page
                    if page.page_number not in active_question.source_pages:
                        active_question.source_pages.append(page.page_number)

                    opt_idx = len(active_question.options)
                    active_option = ParsedOption(key=opt_key, text=opt_rem, order_index=opt_idx)
                    active_question.options.append(active_option)
                    continue

                # 3. Continuation text
                if active_option:
                    active_option.text = f"{active_option.text} {line}".strip()
                    if active_question and page.page_number not in active_question.source_pages:
                        active_question.source_pages.append(page.page_number)
                elif active_question:
                    active_question.question_text = f"{active_question.question_text} {line}".strip()
                    if page.page_number not in active_question.source_pages:
                        active_question.source_pages.append(page.page_number)
                else:
                    if len(line) > 25 and "?" in line and not QuestionParserService.is_instruction_text(line):
                        active_question = ParsedQuestion(
                            question_number=None,
                            question_text=line,
                            options=[],
                            source_pages=[page.page_number],
                        )
                        active_option = None

        # Finalize trailing question
        if active_question:
            cls._finalize_question(active_question)
            if cls._is_valid_question(active_question):
                questions.append(active_question)

        return questions

    @classmethod
    def _is_valid_question(cls, question: ParsedQuestion) -> bool:
        """Determines if a question is valid and not instruction text or empty."""
        if not question or not question.question_text.strip():
            return False
        if QuestionParserService.is_instruction_text(question.question_text):
            return False
        return True

    @classmethod
    def _finalize_question(cls, question: ParsedQuestion):
        """Performs post-processing, inline option detection, and type classification."""
        if not question.options:
            inline_opts = QuestionParserService.extract_inline_options(question.question_text)
            if inline_opts:
                question.options = inline_opts
                first_opt_key = inline_opts[0].key
                split_idx = question.question_text.find(f"({first_opt_key})")
                if split_idx == -1:
                    split_idx = question.question_text.find(f"{first_opt_key}.")
                if split_idx != -1:
                    question.question_text = question.question_text[:split_idx].strip()

        question.question_type = QuestionParserService.classify_type(
            question.question_text, question.options
        )

