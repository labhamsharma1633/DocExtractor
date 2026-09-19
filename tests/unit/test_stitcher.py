import uuid
import pytest
from app.schemas.page import PageContent
from app.services.stitcher_service import MultiPageStitcherService


def test_multipage_question_stitching():
    doc_id = uuid.uuid4()
    
    # Page 1 contains Q1 complete and Q2 starting with option A and B
    page1_text = """
1. What is 2 + 2?
A. 3
B. 4
C. 5
D. 6

2. Which of the following statements regarding TCP congestion control are accurate?
A. Slow start doubles congestion window every RTT.
B. Fast recovery handles duplicate ACKs.
"""
    page1 = PageContent(
        document_id=doc_id,
        page_number=1,
        extracted_text=page1_text,
        ocr_used=False,
    )

    # Page 2 continues Q2 with option C and D, and starts Q3
    page2_text = """
C. TCP Vegas relies entirely on packet loss for delay detection.
D. Congestion avoidance increases window linearly.

3. Name the primary function of an ARP request.
"""
    page2 = PageContent(
        document_id=doc_id,
        page_number=2,
        extracted_text=page2_text,
        ocr_used=False,
    )

    questions = MultiPageStitcherService.extract_questions_from_pages([page1, page2])

    assert len(questions) == 3

    # Q1
    assert questions[0].question_number == "1"
    assert questions[0].source_pages == [1]
    assert len(questions[0].options) == 4

    # Q2: Spanned across pages 1 and 2!
    assert questions[1].question_number == "2"
    assert questions[1].source_pages == [1, 2]
    assert len(questions[1].options) == 4
    assert questions[1].options[0].key == "A"
    assert questions[1].options[2].key == "C"
    assert questions[1].options[3].key == "D"

    # Q3
    assert questions[2].question_number == "3"
    assert questions[2].source_pages == [2]
    assert questions[2].question_type == "SHORT_ANSWER"


def test_instruction_section_filtering():
    doc_id = uuid.uuid4()

    page1_text = """
General Instructions:
1. Immediately fill in the particulars on this page of the test booklet.
2. The test is of 180 minutes duration and the Test Booklet contains 180 questions.
3. Each correct answer will give 4 marks while 1 mark will be deducted for a wrong MCQ response.

OMR Instructions:
1. Use blue/black dark ballpoint pens.
2. Darken the bubbles completely.

Name of the Student: Test Student
Roll Number: 123456
"""
    page1 = PageContent(
        document_id=doc_id,
        page_number=1,
        extracted_text=page1_text,
        ocr_used=False,
    )

    page2_text = """
Q1. What is the SI unit of force?
A. Joule
B. Newton
C. Watt
D. Pascal
"""
    page2 = PageContent(
        document_id=doc_id,
        page_number=2,
        extracted_text=page2_text,
        ocr_used=False,
    )

    questions = MultiPageStitcherService.extract_questions_from_pages([page1, page2])

    # Instruction section on page 1 must be ignored, leaving only Q1 from page 2
    assert len(questions) == 1
    assert questions[0].question_number == "1"
    assert "SI unit of force" in questions[0].question_text
    assert len(questions[0].options) == 4

