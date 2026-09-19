# Document Processing & Question Extraction Service — Architecture

## 1. Executive Summary
The Document Processing & Question Extraction Service is an asynchronous, scalable backend service engineered to ingest diverse examination papers and question bank documents (digital PDFs, scanned PDFs, JPEG/PNG images) and convert them into structured, validated, machine-readable question objects with explainable confidence scoring, answer-key matching, and human-in-the-loop review facilities.

---

## 2. High-Level Architecture Diagram

```
+---------------------------------------------------------------------------------+
|                                 Client Applications                             |
|                           (Swagger UI / Postman / Tests)                        |
+----------------------------------------+----------------------------------------+
                                         | HTTP REST (JSON / Multipart)
                                         v
+---------------------------------------------------------------------------------+
|                               FastAPI Application                               |
| - Authentication Middleware (Bcrypt & JWT Bearer Guards)                        |
| - MIME & Magic Byte Validation                                                  |
| - Storage Abstraction Layer (UUID Storage)                                      |
| - Synchronous Read APIs (Documents, Questions, Answers, Reviews)                |
+-------------------+-----------------------------------------+-------------------+
                    |                                         |
     Dispatches Job |                                         | Persists initial
                    v                                         v metadata
+-------------------+--------------------+   +----------------+-------------------+
|            Redis Broker                |   |          PostgreSQL Database       |
|       (Celery Distributed Queue)       |   |         (ACID Relational Data)     |
+-------------------+--------------------+   +----------------+-------------------+
                    |                                         ^
        Pulls task  |                                         | Updates stage,
                    v                                         | pages, questions,
+-------------------+--------------------+                    | reviews, answers
|             Celery Worker              |--------------------+
+-------------------+--------------------+
                    |
      +-------------+-------------+
      |                           |
      v                           v
[ Ingestion & OCR ]       [ Question Parsing ]
- PyMuPDF Vector Text     - Regex Anchors (1., Q1, 01))
- Rasterizer (300 DPI)    - Option Extractor (A., (a), 1.)
- OpenCV Preprocessor     - Multi-Page Continuity Buffer
- Tesseract OCR Wrapper   - Type Classifier (MCQ, TRUE_FALSE...)
      |                           |
      +-------------+-------------+
                    |
                    v
       [ Answer Matching & Confidence ]
       - Answer Key parser
       - Document Relationships (External keys)
       - Explainable scoring formula (0.0 to 1.0)
       - Review item generator
```

---

## 3. Detailed Processing Pipeline

1. **Ingestion & Validation**:
   - Validates file size (max 20MB) and true MIME type via magic byte inspection (`%PDF`, `\xff\xd8\xff`, `\x89PNG`).
   - Assigns a cryptographic UUID storage name in `./data/uploads/` to prevent directory traversal.
   - Enqueues job in Celery worker queue and returns `202 Accepted` immediately.

2. **Normalized Page Extraction**:
   - For digital PDFs: PyMuPDF extracts text layer directly.
   - For scanned PDFs & Images: PyMuPDF rasterizes pages at 300 DPI $\rightarrow$ OpenCV applies Grayscale, Noise Removal, Deskewing, and Otsu Binarization $\rightarrow$ Tesseract extracts text and word-level confidences.
   - Stores normalized `DocumentPage` records.

3. **Question & Option Parsing**:
   - `QuestionParserService` detects question numbering patterns (`1.`, `1)`, `Q1.`, `01.`, `Question 1`) and options (`A.`, `(a)`, `(1)`, inline options).
   - `MultiPageStitcherService` maintains an open question buffer across page boundaries, associating `source_pages: [N, N+1]`.
   - `QuestionParserService` classifies types: `MCQ`, `TRUE_FALSE`, `SHORT_ANSWER`, `DESCRIPTIVE`, `UNKNOWN`.

4. **Answer Key Extraction & Resolution**:
   - `AnswerService` scans document for `"Answer Key"` blocks and parses mappings (`1 -> B`, `2 -> A`).
   - Also resolves cross-document answer keys via `DocumentRelationship` records.
   - Associates answers with questions and marks correct options (`is_correct = True`).

5. **Explainable Confidence Scoring & Review Engine**:
   - Evaluates structural signals: Question text presence ($+0.30$), Question number detected ($+0.20$), Options valid ($+0.25$), OCR/Source quality ($+0.15$), Answer match ($+0.10$).
   - Categorizes status: $\ge 0.85$ (`EXTRACTED`), $0.60–0.84$ (`PARTIAL`), $< 0.60$ (`REVIEW`).
   - Flags granular `ReviewItem` entries with severity ratings for human operator review.

---

## 4. Relational Database Schema

```
Users (id, email, hashed_password, created_at, updated_at)
  └── Documents (id, user_id, filename, mime_type, processing_status, processing_stage, overall_confidence, ...)
        ├── DocumentPages (id, document_id, page_number, extracted_text, ocr_used, ocr_confidence, image_path, ...)
        ├── Questions (id, document_id, question_number, question_text, question_type, confidence_score, extraction_status, matched_answer, ...)
        │     ├── QuestionOptions (id, question_id, option_key, option_text, is_correct, order_index)
        │     ├── QuestionSources (id, question_id, page_number, bounding_box)
        │     └── ReviewItems (id, document_id, question_id, review_type, severity, message, confidence, is_resolved)
        ├── AnswerKeys (id, document_id, raw_key_text, parsed_answers, page_number)
        └── DocumentRelationships (id, source_document_id, related_document_id, relationship_type)
```

---

## 5. Concurrency & Scalability

- **Horizontal Worker Scaling**: Workers are stateless and consume tasks from Redis. To scale processing throughput under high upload loads, increase Celery worker concurrency:
  `docker compose up --scale worker=4`
- **FastAPI Asynchronous Web Layer**: ASGI event-loop handles high concurrent HTTP upload requests and non-blocking database queries without stalling.
