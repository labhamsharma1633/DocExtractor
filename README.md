# DocExtractor — Universal Document Question & Diagram Extraction Service

### 👤 Project Information
* **Student Name**: Labham Sharma
* **Registration Number**: 12301046
* 🌐 **Live Web Application**: [https://docextractor-iv9b.onrender.com/](https://docextractor-iv9b.onrender.com/)
* 🎥 **Video Demonstration**: [https://youtu.be/lAebZnGRl44](https://youtu.be/lAebZnGRl44)
* 💻 **GitHub Repository**: [https://github.com/labhamsharma1633/DocExtractor](https://github.com/labhamsharma1633/DocExtractor)
* 📚 **API Docs (Swagger)**: [https://docextractor-iv9b.onrender.com/docs](https://docextractor-iv9b.onrender.com/docs)

---

## Key Features

* **Universal Ingestion**: Ingests Digital PDFs, Scanned PDFs, JPG, and PNG images into a normalized page representation.
* **Asynchronous Processing Pipeline**: Decoupled HTTP API and Celery workers connected via Redis message queue with real-time stage tracking (`OCR_PROCESSING`, `QUESTION_EXTRACTION`, `ANSWER_MATCHING`, `VALIDATION`, `COMPLETED`).
* **Multi-Page Question Reconstruction**: Preserves cross-page continuity and provenance (`source_pages: [1, 2]`) when questions span page boundaries.
* **Flexible Numbering & Option Extraction**: Normalizes numbering styles (`1.`, `1)`, `Q1.`, `Q.1`, `Question 1`, `01.`) and options (`A.`, `(a)`, `(1)`, inline options).
* **Automatic Answer Matching**: Identifies answer keys in the document or associates separate answer key documents via document relationships.
* **Explainable Confidence & Human Review**: Calculates deterministic, signal-based confidence scores ($0.0$–$1.0$) and flags granular review items (`MISSING_OPTIONS`, `OCR_UNCERTAINTY`, `SPANNING_PAGES`) with human resolution workflows.
* **Multi-Tenant Security**: Bcrypt password hashing, JWT Bearer authentication, and ownership isolation on all document resources.

---

## Architecture Overview

```
Client (Swagger / Postman)
    │  HTTP REST / JWT
    ▼
FastAPI Application (Auth, Validation, Storage Abstraction)
    ├──► PostgreSQL (ACID Relational Storage)
    └──► Redis Broker
           │
           ▼
     Celery Worker (PyMuPDF -> OpenCV -> OCR -> Question Parser -> Stitcher -> Answer Matcher -> Confidence Evaluator)
           │
           └──► PostgreSQL (Updates Pages, Questions, Options, Answers, Reviews)
```

---

## Quickstart with Docker Compose

```bash
# Clone and start all services
docker compose up --build
```
Once started:
* **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## Running Automated Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run full pytest suite (29 tests)
pytest -v tests/
```

---

## Postman Collection

* Collection: `postman/doc_extractor.postman_collection.json`
* Environment: `postman/local_environment.postman_environment.json`

---

## Project Structure

```
doc-question-extractor/
├── app/
│   ├── api/                     # Route handlers (auth, documents, questions, answers, reviews, relationships)
│   ├── core/                    # Config, Security (Bcrypt/JWT), Exceptions, Logging
│   ├── db/                      # SQLAlchemy 2.0 Base, Session, and Relational Models
│   ├── schemas/                 # Pydantic Request & Response Models
│   ├── services/                # Pipeline, Parser, Stitcher, OCR, Preprocessing, Storage, Confidence
│   └── workers/                 # Celery app and asynchronous task definitions
├── docs/                        # Architecture, Design Decisions, and Demo walkthroughs
├── migrations/                  # Alembic database migration scripts
├── postman/                     # Postman collection & environment JSON
├── samples/                     # Synthetic test documents (clean PDF, multi-page, images, answer keys)
├── tests/                       # Unit and integration pytest test suite (29 tests)
├── docker-compose.yml           # Production Docker Compose orchestration
├── Dockerfile                   # Python 3.11 container with Tesseract & OpenCV dependencies
├── requirements.txt             # Locked dependencies
└── README.md
```

---

## Documentation Links

* [Architecture Guide](file:///C:/Users/labha/.gemini/antigravity-ide/scratch/doc-question-extractor/docs/architecture.md)
* [Design Decisions & Trade-offs](file:///C:/Users/labha/.gemini/antigravity-ide/scratch/doc-question-extractor/docs/design-decisions.md)
* [Demonstration Walkthrough](file:///C:/Users/labha/.gemini/antigravity-ide/scratch/doc-question-extractor/docs/demo.md)
