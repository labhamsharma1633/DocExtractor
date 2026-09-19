import pytest
from app.services.region_classifier import RegionClassifier, RegionType
from app.services.universal_parser import UniversalQuestionParser, OptionCandidate, RawQuestionCandidate
from app.services.confidence_service import ConfidenceService


def test_scenario_1_clean_mcq():
    lines = [
        "1. What is the capital of France?",
        "A. London",
        "B. Paris",
        "C. Berlin",
        "D. Madrid"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert candidates[0].question_number == "1"
    assert candidates[0].question_text == "What is the capital of France?"
    assert len(candidates[0].options) == 4
    assert candidates[0].options[1].key == "B"
    assert candidates[0].options[1].text == "Paris"


def test_scenario_2_and_27_instruction_filtering():
    """
    CRITICAL TEST: Ensures exam instructions and metadata DO NOT become questions.
    """
    lines = [
        "Immediately fill in the particulars on this page of the test booklet.",
        "The test is of 180 minutes duration and contains 180 questions.",
        "Instructions: Each question carries four marks.",
        "Candidate Name: John Doe",
        "Roll No: 123456",
        "1. Which of the following is an element?",
        "A. Water",
        "B. Oxygen",
        "C. Salt",
        "D. Sugar"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)

    # Must extract ONLY Q1, ignoring instructions
    assert len(candidates) == 1
    assert candidates[0].question_number == "1"
    assert candidates[0].question_text == "Which of the following is an element?"


def test_scenario_3_question_without_number():
    lines = [
        "Which of the following numbers is prime?",
        "A. 4",
        "B. 7",
        "C. 9",
        "D. 12"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert candidates[0].question_number is None
    assert "prime" in candidates[0].question_text
    assert len(candidates[0].options) == 4


def test_scenario_4_different_numbering():
    numberings = [
        "1. What is X?",
        "1) What is X?",
        "Q1. What is X?",
        "Question 1: What is X?",
        "Que 1. What is X?",
        "01) What is X?"
    ]
    for text in numberings:
        is_start, num, rem = UniversalQuestionParser.is_question_start(text)
        assert is_start is True
        assert num in ["1", "01"]
        assert rem == "What is X?"


def test_scenario_6_parenthetical_options():
    lines = [
        "1. Select the correct option.",
        "(a) First option",
        "(b) Second option",
        "(c) Third option",
        "(d) Fourth option"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert len(candidates[0].options) == 4
    assert candidates[0].options[0].key == "A"
    assert candidates[0].options[0].text == "First option"


def test_scenario_7_horizontal_options():
    lines = [
        "1. What is 2 + 2?",
        "A. 2    B. 4    C. 6    D. 8"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert len(candidates[0].options) == 4
    assert candidates[0].options[1].key == "B"
    assert candidates[0].options[1].text == "4"


def test_scenario_8_multiline_options():
    lines = [
        "1. What is gravity?",
        "A. Gravity is a fundamental force of nature that attracts a body",
        "   toward the center of the earth, or toward any other physical body having mass.",
        "B. A chemical reaction."
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert len(candidates[0].options) == 2
    assert "toward the center" in candidates[0].options[0].text


def test_scenario_9_spanning_pages():
    pages = [
        {"page_number": 1, "raw_text": "1. Consider the following circuit and determine the current flowing through\nA. 2A\nB. 4A"},
        {"page_number": 2, "raw_text": "C. 6A\nD. 8A"}
    ]
    candidates = UniversalQuestionParser.parse_document_pages(pages)
    assert len(candidates) == 1
    assert candidates[0].question_number == "1"
    assert len(candidates[0].options) == 4
    assert candidates[0].source_pages == [1, 2]


def test_scenario_12_assertion_reason():
    lines = [
        "1. Assertion (A): Water boils at 100 degrees Celsius at sea level.",
        "Reason (R): Atmospheric pressure affects boiling point.",
        "A. Both A and R are true",
        "B. Both A and R are false"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert candidates[0].question_type == "ASSERTION_REASON"


def test_scenario_14_true_false():
    lines = [
        "1. TCP is a connection-oriented protocol.",
        "A. True",
        "B. False"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert candidates[0].question_type == "TRUE_FALSE"


def test_scenario_15_fill_in_the_blank():
    lines = [
        "1. The capital of France is ______."
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert candidates[0].question_type == "FILL_IN_THE_BLANK"


def test_scenario_16_descriptive_question():
    lines = [
        "1. Explain the OSI model seven layers in detail."
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert candidates[0].question_type == "DESCRIPTIVE"


def test_scenario_17_passage_based_questions():
    lines = [
        "Read the following passage and answer questions 1–2.",
        "Passage: Artificial Intelligence is revolutionizing modern technology...",
        "1. What is the passage about?",
        "A. AI    B. Chemistry",
        "2. Which statement is correct?",
        "A. Option 1    B. Option 2"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 2
    assert candidates[0].context is not None
    assert "Artificial Intelligence" in candidates[0].context
    assert candidates[1].context == candidates[0].context


def test_scenario_26_header_footer_filtering():
    lines = [
        "Page 1 of 24",
        "NEET 2026 TEST PAPER",
        "1. What is energy?",
        "A. Joule",
        "B. Newton",
        "Copyright 2026 All Rights Reserved"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert candidates[0].question_number == "1"
    assert "Copyright" not in candidates[0].question_text


def test_header_prefix_removal():
    lines = [
        "39. NEET When 20 g of sugar is dissolved in 200 mL of H2O, the mass by volume percentage of sugar is:",
        "1 10%    2 15%    3 20%    4 25%"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert candidates[0].question_number == "39"
    assert not candidates[0].question_text.startswith("NEET")
    assert candidates[0].question_text.startswith("When 20 g of sugar")
    assert len(candidates[0].options) == 4


def test_parenthetical_numeric_options():
    lines = [
        "78. 1 g atom of nitrogen represents:",
        "1 14 g nitrogen",
        "2 2.24 litre of N2 at STP",
        "3 22.4 litre of N2 at STP",
        "4 6.023 x 10^23 molecules of N2"
    ]
    page = [{"page_number": 1, "raw_text": "\n".join(lines)}]
    candidates = UniversalQuestionParser.parse_document_pages(page)
    assert len(candidates) == 1
    assert len(candidates[0].options) == 4
    assert candidates[0].options[0].text == "14 g nitrogen"
    assert candidates[0].options[3].text == "6.023 x 10^23 molecules of N2"

