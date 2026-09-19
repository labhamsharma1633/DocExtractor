# Demonstration & Evaluation Guide

This guide walks you through running, testing, and evaluating the Document Processing & Question Extraction Service.

---

## 1. Starting the Application

### Option A: Running with Docker Compose (Recommended)
```bash
docker compose up --build
```
Services started:
* **API Service**: `http://localhost:8000`
* **Swagger UI Documentation**: `http://localhost:8000/docs`
* **PostgreSQL**: `localhost:5432`
* **Redis**: `localhost:6379`
* **Celery Worker**: Background task executor

### Option B: Running Locally with Python
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 2. Interactive Testing via Swagger UI (`/docs`)

1. Open `http://localhost:8000/docs` in your browser.
2. Register a new user:
   * Execute `POST /api/v1/auth/register` with:
     ```json
     {
       "email": "evaluator@example.com",
       "password": "Password123!",
       "full_name": "Evaluation Lead"
     }
     ```
3. Authenticate:
   * Execute `POST /api/v1/auth/login` to obtain your `access_token`.
   * Click the **Authorize** button at the top of Swagger and enter: `Bearer <your_token>`.
4. Upload Examination Documents:
   * Execute `POST /api/v1/documents` and select `samples/clean_digital.pdf`.
   * Copy the returned `document_id`.
5. Check Document Status & Metrics:
   * Execute `GET /api/v1/documents/{document_id}`.
   * View `processing_status: COMPLETED`, `questions_count: 4`, `overall_confidence: 1.0`.
6. Retrieve Structured Questions:
   * Execute `GET /api/v1/documents/{document_id}/questions`.
   * Observe normalized MCQs with options and matched answer key.
7. Test Multi-Page Continuation:
   * Upload `samples/multipage_question.pdf`.
   * Observe that Question 2 was stitched across Page 1 and Page 2 with `source_pages: [1, 2]`.
8. Test Human Review & Correction:
   * Query `GET /api/v1/documents/{document_id}/review-items`.
   * Resolve a review item via `PATCH /api/v1/review-items/{id}/resolve`.
   * Correct a question via `PATCH /api/v1/questions/{id}`.

---

## 3. Automated Test Suite Execution

Run the complete automated test suite (all 29 unit & integration tests):
```bash
pytest -v tests/
```
Output:
```
======================== 29 passed in 8.55s ========================
```

---

## 4. Postman Collection

1. Import `postman/doc_extractor.postman_collection.json` into Postman.
2. Import `postman/local_environment.postman_environment.json`.
3. Run the requests sequentially from Folder 1 (Authentication) to Folder 5 (Review Items).
