import os
import uuid
from typing import List
import fitz  # PyMuPDF
import cv2

from app.core.config import settings
from app.core.logging import logger
from app.schemas.page import PageContent
from app.services.ocr_service import OCRService
from app.services.preprocess_service import ImagePreprocessService


class PageExtractionService:
    """Orchestrates PDF text extraction, rasterization, and OCR preprocessing into normalized PageContent."""

    def __init__(self, ocr_service: OCRService = None):
        self.ocr_service = ocr_service or OCRService()

    def process_document_to_pages(
        self, file_path: str, document_id: uuid.UUID, mime_type: str
    ) -> List[PageContent]:
        """Main entrypoint: parses PDF or Image and returns normalized PageContent objects."""
        if mime_type == "application/pdf":
            return self._process_pdf(file_path, document_id)
        elif mime_type in ["image/jpeg", "image/jpg", "image/png"]:
            return self._process_image(file_path, document_id)
        else:
            raise ValueError(f"Unsupported MIME type: {mime_type}")

    def _process_pdf(self, file_path: str, document_id: uuid.UUID) -> List[PageContent]:
        doc = fitz.open(file_path)
        pages_content: List[PageContent] = []

        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            page = doc[page_idx]

            # Always render page image for preview & diagram extraction
            page_img_filename = f"{document_id}_page_{page_number}.png"
            page_img_path = os.path.join(settings.PAGE_IMAGE_DIR, page_img_filename)
            page_img_url = f"/page_images/{page_img_filename}"
            
            try:
                pix = page.get_pixmap(dpi=150)
                pix.save(page_img_path)
            except Exception as e:
                logger.warning(f"Failed to render pixmap for page {page_number}: {e}")

            # 1. Layout-Aware Text Extraction (Supports Two-Column & Multi-Column PDFs)
            blocks = page.get_text("blocks")
            # Filter text blocks (block_type == 0)
            text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]

            if text_blocks:
                mid_x = page.rect.width / 2.0
                has_left = any(b[0] < mid_x and b[2] <= mid_x + 40 for b in text_blocks)
                has_right = any(b[0] >= mid_x - 40 for b in text_blocks)

                if has_left and has_right:
                    # Two-Column Layout: Read left column top-to-bottom, then right column
                    left_col = sorted([b for b in text_blocks if b[0] < mid_x], key=lambda b: (b[1], b[0]))
                    right_col = sorted([b for b in text_blocks if b[0] >= mid_x], key=lambda b: (b[1], b[0]))
                    direct_text = "\n".join(b[4].strip() for b in left_col + right_col)
                else:
                    # Single Column Layout: Read top-to-bottom
                    ordered = sorted(text_blocks, key=lambda b: (b[1], b[0]))
                    direct_text = "\n".join(b[4].strip() for b in ordered)
            else:
                direct_text = page.get_text("text").strip()

            # If digital text exists with sufficient character count, use direct extraction
            if len(direct_text) > 40:
                logger.info(f"Doc {document_id} Page {page_number}: layout-aware direct text extracted ({len(direct_text)} chars).")
                pages_content.append(
                    PageContent(
                        document_id=document_id,
                        page_number=page_number,
                        extracted_text=direct_text,
                        ocr_used=False,
                        ocr_confidence=100.0,
                        image_path=page_img_url,
                        rotation=0,
                        page_metadata={"source": "digital_pdf", "char_count": len(direct_text)},
                    )
                )

            else:
                # 2. Scanned PDF page -> Rasterize at 300 DPI and run OCR
                logger.info(f"Doc {document_id} Page {page_number}: scanned page detected. Rasterizing at {settings.OCR_DPI} DPI...")
                pix_high = page.get_pixmap(dpi=settings.OCR_DPI)
                pix_high.save(page_img_path)

                # Preprocess with OpenCV
                preprocessed_img, angle = ImagePreprocessService.preprocess_for_ocr(page_img_path)
                
                # Run OCR
                ocr_text, ocr_conf = self.ocr_service.extract_text_and_confidence(preprocessed_img)
                
                # If OCR didn't find anything but digital text had a little bit, fallback to digital
                final_text = ocr_text if ocr_text else direct_text

                pages_content.append(
                    PageContent(
                        document_id=document_id,
                        page_number=page_number,
                        extracted_text=final_text,
                        ocr_used=True,
                        ocr_confidence=ocr_conf,
                        image_path=page_img_url,
                        rotation=int(angle),
                        page_metadata={
                            "source": "scanned_pdf",
                            "skew_angle": angle,
                            "raster_dpi": settings.OCR_DPI,
                        },
                    )
                )


        doc.close()
        return pages_content

    def _process_image(self, file_path: str, document_id: uuid.UUID) -> List[PageContent]:
        """Processes a standalone JPG or PNG image."""
        logger.info(f"Doc {document_id}: Processing image file for OCR extraction...")
        preprocessed_img, angle = ImagePreprocessService.preprocess_for_ocr(file_path)
        ocr_text, ocr_conf = self.ocr_service.extract_text_and_confidence(preprocessed_img)

        return [
            PageContent(
                document_id=document_id,
                page_number=1,
                extracted_text=ocr_text,
                ocr_used=True,
                ocr_confidence=ocr_conf,
                image_path=file_path,
                rotation=int(angle),
                page_metadata={"source": "image", "skew_angle": angle},
            )
        ]
