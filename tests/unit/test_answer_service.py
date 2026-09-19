import pytest
from app.services.answer_service import AnswerService
from app.services.parser_service import ParsedOption, ParsedQuestion


def test_answer_pair_parsing():
    raw_key = """
Answer Key:
1. B
2 - C
3) A
Q4: D
05. True
"""
    answers = AnswerService.parse_answer_pairs(raw_key)
    assert answers == {
        "1": "B",
        "2": "C",
        "3": "A",
        "4": "D",
        "5": "TRUE",
    }


def test_match_answers_to_questions():
    q1 = ParsedQuestion(
        question_number="1",
        question_text="What is UDP?",
        options=[
            ParsedOption("A", "Connection oriented"),
            ParsedOption("B", "Connectionless"),
        ],
        source_pages=[1],
    )
    q2 = ParsedQuestion(
        question_number="2",
        question_text="Unmatched question?",
        options=[ParsedOption("A", "Yes"), ParsedOption("B", "No")],
        source_pages=[1],
    )

    answer_map = {"1": "B"}
    AnswerService.match_answers_to_questions([q1, q2], answer_map)

    # Q1 matched
    assert q1.matched_answer == "B"
    assert q1.options[0].is_correct is False
    assert q1.options[1].is_correct is True

    # Q2 unmatched
    assert q2.matched_answer is None
    assert q2.options[0].is_correct is None
