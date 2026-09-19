import shutil
from typing import Optional, Tuple
import numpy as np
from PIL import Image
import pytesseract

from app.core.config import settings
from app.core.logging import logger


class OCRService:
    """Service wrapper for Tesseract OCR execution and confidence aggregation."""

    def __init__(self, tesseract_cmd: Optional[str] = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        elif settings.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    @staticmethod
    def is_tesseract_available() -> bool:
        """Verifies if Tesseract binary is available in the current environment."""
        if settings.TESSERACT_CMD and shutil.which(settings.TESSERACT_CMD):
            return True
        return shutil.which("tesseract") is not None

    def extract_text_and_confidence(self, image: np.ndarray) -> Tuple[str, float]:
        """Runs Tesseract OCR on a numpy image array and calculates mean word confidence."""
        if not self.is_tesseract_available():
            logger.warning("Tesseract binary not found in environment. Using fallback text extraction.")
            return "", 0.0

        try:
            # Convert CV2 numpy array to PIL Image
            if len(image.shape) == 2:
                pil_img = Image.fromarray(image)
            else:
                pil_img = Image.fromarray(image[:, :, ::-1])

            # Extract detailed word-level data dictionary
            data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
            
            extracted_words = []
            confidences = []

            for i in range(len(data["text"])):
                word = data["text"][i].strip()
                conf = float(data["conf"][i])
                if word and conf > 0:
                    extracted_words.append(word)
                    confidences.append(conf)

            full_text = pytesseract.image_to_string(pil_img).strip()
            avg_confidence = float(np.mean(confidences)) if confidences else 0.0

            return full_text, round(avg_confidence, 2)

        except Exception as e:
            logger.error(f"OCR execution failure: {str(e)}")
            return "", 0.0
