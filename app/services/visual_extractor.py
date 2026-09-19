import os
import fitz  # PyMuPDF
from typing import Dict, List, Optional, Tuple, Any
from app.core.config import settings
from app.services.universal_parser import RawQuestionCandidate


class VisualExtractorService:
    """
    Universal spatial layout-aware visual extractor.
    Extracts embedded diagrams, raster images, and vector graphics from PDF pages,
    filters out headers, footers, and watermarks, and accurately associates each diagram
    with its corresponding question candidate.
    """

    VISUAL_KEYWORDS = [
        "circuit", "diagram", "figure", "graph", "chart", "map", "table",
        "shown below", "given below", "refer to", "based on the figure",
        "see figure", "illustration", "image", "chemical structure",
        "shown in figure", "following figure", "vector diagram",
        "in the adjoining", "given figure", "represented in figure"
    ]

    @classmethod
    def is_watermark_or_header_footer(cls, bbox: Tuple[float, float, float, float], page_rect: fitz.Rect) -> bool:
        """Determines if an image bbox is a footer logo, header banner, or central watermark."""
        x0, y0, x1, y1 = bbox
        width = x1 - x0
        height = y1 - y0

        # Footer margin (bottom 80pt)
        if y0 > page_rect.height - 75:
            return True

        # Header margin (top 45pt)
        if y1 < 45:
            return True

        # Large center watermark (covers large area in the middle of page)
        if width > 240 and height > 240:
            return True

        # Tiny icons / bullets (< 15x15)
        if width < 15 and height < 15:
            return True

        return False

    @classmethod
    def extract_visuals_for_questions(
        cls,
        doc_path: str,
        candidates: List[RawQuestionCandidate],
        output_dir: Optional[str] = None
    ) -> List[RawQuestionCandidate]:
        """
        Scans PDF pages spatially for image/diagram blocks, isolates question diagrams
        from watermarks, crops vector figures if needed, and links images to questions.
        """
        if not os.path.exists(doc_path):
            return candidates

        save_dir = settings.PAGE_IMAGE_DIR
        os.makedirs(save_dir, exist_ok=True)

        # Handle direct image files (PNG/JPG)
        if doc_path.lower().endswith((".png", ".jpg", ".jpeg")):
            for candidate in candidates:
                candidate.requires_visual_context = True
                image_filename = os.path.basename(doc_path)
                candidate.images.append({
                    "page": 1,
                    "path": f"/page_images/{image_filename}",
                    "bbox": None
                })
            return candidates

        if not doc_path.lower().endswith(".pdf"):
            return candidates

        try:
            doc = fitz.open(doc_path)

            for candidate in candidates:
                lower_text = candidate.question_text.lower()
                has_visual_keyword = any(kw in lower_text for kw in cls.VISUAL_KEYWORDS)
                if has_visual_keyword:
                    candidate.requires_visual_context = True

                for page_num in candidate.source_pages:
                    if page_num < 1 or page_num > len(doc):
                        continue

                    page = doc[page_num - 1]
                    mid_x = page.rect.width / 2.0

                    # 1. Locate Question Anchor on Page
                    q_anchor = None
                    if candidate.question_number:
                        rects = page.search_for(f"Q{candidate.question_number}")
                        if not rects:
                            rects = page.search_for(f"Q {candidate.question_number}")
                        if not rects:
                            rects = page.search_for(f"Q.{candidate.question_number}")
                        if rects:
                            q_anchor = rects[0]

                    if not q_anchor and len(candidate.question_text.strip()) >= 15:
                        stem = candidate.question_text.strip()[:30]
                        rects = page.search_for(stem)
                        if rects:
                            q_anchor = rects[0]

                    # 2. Extract Valid Raster Images in the Question's Column
                    img_infos = page.get_image_info(xrefs=True)
                    matched_img = None

                    if q_anchor:
                        is_left = q_anchor.x0 < mid_x
                        col_x0 = 0.0 if is_left else mid_x
                        col_x1 = mid_x if is_left else page.rect.width

                        for info in img_infos:
                            bbox = info.get("bbox")
                            if not bbox or cls.is_watermark_or_header_footer(bbox, page.rect):
                                continue

                            img_mid_x = (bbox[0] + bbox[2]) / 2.0
                            in_col = (img_mid_x < mid_x) if is_left else (img_mid_x >= mid_x)

                            # Check if image is vertically positioned near/below the question
                            if in_col and (q_anchor.y0 - 25 <= bbox[1] <= q_anchor.y0 + 380):
                                matched_img = info
                                break

                    # 3. If matched raster diagram found, extract and save
                    if matched_img:
                        xref = matched_img["xref"]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image.get("ext", "png")

                        q_tag = candidate.question_number or "un"
                        image_filename = f"q_{q_tag}_p{page_num}_{xref}.{image_ext}"
                        image_filepath = os.path.join(save_dir, image_filename)

                        with open(image_filepath, "wb") as f:
                            f.write(image_bytes)

                        relative_path = f"/page_images/{image_filename}"
                        candidate.images.append({
                            "page": page_num,
                            "path": relative_path,
                            "bbox": matched_img.get("bbox")
                        })
                        candidate.requires_visual_context = True

                    # 4. If visual context required (vector drawings / circuits) but no raster image matched
                    elif candidate.requires_visual_context and q_anchor:
                        is_left = q_anchor.x0 < mid_x
                        col_x0 = max(10.0, 0.0 if is_left else mid_x)
                        col_x1 = min(page.rect.width - 10.0, mid_x if is_left else page.rect.width)

                        # Crop the diagram area below question text
                        crop_top = max(0.0, q_anchor.y1)
                        crop_bottom = min(page.rect.height - 75.0, crop_top + 220.0)

                        if crop_bottom > crop_top + 30.0:
                            crop_rect = fitz.Rect(col_x0, crop_top, col_x1, crop_bottom)
                            page_crop_filename = f"crop_q_{candidate.question_number or 'un'}_p{page_num}.png"
                            crop_filepath = os.path.join(save_dir, page_crop_filename)

                            if not os.path.exists(crop_filepath):
                                pix = page.get_pixmap(clip=crop_rect, dpi=160)
                                pix.save(crop_filepath)

                            relative_path = f"/page_images/{page_crop_filename}"
                            candidate.images.append({
                                "page": page_num,
                                "path": relative_path,
                                "bbox": [crop_rect.x0, crop_rect.y0, crop_rect.x1, crop_rect.y1]
                            })

            doc.close()
        except Exception:
            pass

        return candidates
