import pytest
from app.services.parser_service import QuestionParserService, ParsedOption


def test_question_numbering_formats():
    test_lines = [
        ("1. What is TCP?", "1", "What is TCP?"),
        ("1) What is TCP?", "1", "What is TCP?"),
        ("01. What is TCP?", "1", "What is TCP?"),
        ("01) What is TCP?", "1", "What is TCP?"),
        ("Q1. What is TCP?", "1", "What is TCP?"),
        ("Q.1 What is TCP?", "1", "What is TCP?"),
        ("Question 1 What is TCP?", "1", "What is TCP?"),
        ("Que. 1: What is TCP?", "1", "What is TCP?"),
        ("15. Which protocol is connection-oriented?", "15", "Which protocol is connection-oriented?"),
    ]

    for line, expected_num, expected_text in test_lines:
        is_q, q_num, q_text = QuestionParserService.is_question_start(line)
        assert is_q is True, f"Failed to match question line: {line}"
        assert q_num == expected_num, f"Expected {expected_num}, got {q_num} for {line}"
        assert q_text == expected_text


def test_option_formats():
    test_lines = [
        ("A. HyperText Transfer Protocol", "A", "HyperText Transfer Protocol"),
        ("(a) HyperText Transfer Protocol", "A", "HyperText Transfer Protocol"),
        ("B) File Transfer Protocol", "B", "File Transfer Protocol"),
        ("(1) Simple Mail Transfer Protocol", "1", "Simple Mail Transfer Protocol"),
    ]

    for line, expected_key, expected_text in test_lines:
        is_opt, opt_key, opt_text = QuestionParserService.is_option_line(line)
        assert is_opt is True, f"Failed to match option line: {line}"
        assert opt_key.upper() == expected_key
        assert opt_text == expected_text


def test_inline_options_extraction():
    inline_text = "What is HTTP? (A) Protocol (B) Hardware (C) OS (D) Database"
    opts = QuestionParserService.extract_inline_options(inline_text)
    assert len(opts) == 4
    assert [o.key for o in opts] == ["A", "B", "C", "D"]
    assert opts[0].text == "Protocol"
    assert opts[1].text == "Hardware"


def test_question_type_classification():
    # MCQ with 4 options
    mcq_opts = [
        ParsedOption("A", "Apple"),
        ParsedOption("B", "Banana"),
        ParsedOption("C", "Cherry"),
        ParsedOption("D", "Date"),
    ]
    assert QuestionParserService.classify_type("Select a fruit:", mcq_opts) == "MCQ"

    # True/False with options
    tf_opts = [ParsedOption("A", "True"), ParsedOption("B", "False")]
    assert QuestionParserService.classify_type("Is the Earth round?", tf_opts) == "TRUE_FALSE"

    # Descriptive
    assert QuestionParserService.classify_type("Explain the Raft consensus algorithm in detail.", []) == "DESCRIPTIVE"

    # Short Answer
    assert QuestionParserService.classify_type("What is the default port for DNS?", []) == "SHORT_ANSWER"
