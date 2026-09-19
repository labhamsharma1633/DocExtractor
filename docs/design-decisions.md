# Document Processing & Question Extraction Service — Design Decisions & Trade-offs

## 1. Normalized Page Representation
* **Decision**: Decouple document ingestion from question extraction by producing a standard `PageContent` object.
* **Rationale**: Examination material comes in diverse physical formats (vector PDFs, scanned multi-page PDFs, single PNG photos). By having `PageExtractionService` convert all incoming formats into normalized page models (`extracted_text`, `ocr_used`, `ocr_confidence`, `page_number`), downstream parser, stitcher, and answer-matching services operate on a single uniform representation without format branching.

---

## 2. Deterministic Regex State Machine vs. Pure LLM Architecture
* **Decision**: Implement a robust deterministic anchor parser as the primary extraction engine, with pluggable AI assist reserved for ambiguous structures with strict Pydantic validation.
* **Trade-off Analysis**:
  * *Pure LLM (`PDF -> LLM -> DB`)*: Prone to hallucination, non-deterministic question numbering, rate limits, high monetary costs, and network latency.
  * *Deterministic State Machine*: Instant execution ($<50$ ms), $100\%$ free, zero hallucination of question numbers or options, and fully explainable.
* **Untrusted AI Handling**: When AI is invoked, output must strictly validate against Pydantic schemas. Any validation failure triggers a `ReviewItem` rather than corrupting the persistent database.

---

## 3. Explainable Confidence Scoring vs. Black-Box Metrics
* **Decision**: Compute confidence scores between $0.0$ and $1.0$ through transparent, weighted structural signal checks.
* **Formula Breakdown**:
  * $+0.30$: Question text detected and length $>10$ characters
  * $+0.20$: Question numbering detected and ordered
  * $+0.25$: Options structured correctly (for MCQs, $\ge 4$ options)
  * $+0.15$: Source fidelity (digital PDF or high OCR confidence $>80\%$)
  * $+0.10$: Answer key entry successfully matched
* **Benefit**: Human reviewers and evaluation teams can immediately understand *why* a question received a low confidence score and what specific signal triggered the review flag.

---

## 4. Multi-Page Continuation Buffer
* **Decision**: Questions that cross page boundaries are maintained in an active candidate accumulator until a definitive new question anchor is detected.
* **Rationale**: In real examination papers, questions frequently begin near the bottom of Page $N$ and list options or clauses on Page $N+1$. Treating page breaks as rigid document boundaries loses critical options and splits questions into fragmented noise. Tracking `source_pages: [N, N+1]` preserves multi-page provenance.

---

## 5. Storage Abstraction Layer
* **Decision**: Define a `StorageService` interface implemented by `LocalStorageService`.
* **Rationale**: Allows 1-file swap to AWS S3, Google Cloud Storage, or MinIO for cloud deployments without altering database models or route handlers.

---

## 6. Known Limitations & Future Roadmap
1. **Mathematical LaTeX Formulas**: Complex handwritten multi-line LaTeX equations in low-res scans may require specialized vision transformers (e.g. Nougat).
2. **Complex Multi-Column Tables**: Multi-column newspapers or side-by-side exam columns benefit from layout-analysis bounding-box segmentation (LayoutLM).
