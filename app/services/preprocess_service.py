import cv2
import numpy as np
from typing import Tuple


class ImagePreprocessService:
    """Provides computer vision preprocessing routines for scanned examination documents."""

    @staticmethod
    def load_image(image_path_or_bytes) -> np.ndarray:
        """Loads an image into OpenCV BGR numpy array."""
        if isinstance(image_path_or_bytes, bytes):
            nparr = np.frombuffer(image_path_or_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            img = cv2.imread(image_path_or_bytes)
        
        if img is None:
            raise ValueError("Failed to load image for preprocessing.")
        return img

    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        """Converts BGR image to single-channel Grayscale."""
        if len(image.shape) == 2:
            return image
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def remove_noise(gray_image: np.ndarray) -> np.ndarray:
        """Applies median blurring to eliminate scanner salt-and-pepper noise."""
        return cv2.medianBlur(gray_image, 3)

    @staticmethod
    def binarize_otsu(gray_image: np.ndarray) -> np.ndarray:
        """Applies Otsu's thresholding to generate a high-contrast binary black & white image."""
        _, thresh = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

    @staticmethod
    def deskew(gray_image: np.ndarray) -> Tuple[np.ndarray, float]:
        """Calculates skew angle and straightens rotated or skewed scans."""
        # Invert colors so text pixels are white (255)
        inverted = cv2.bitwise_not(gray_image)
        coords = np.column_stack(np.where(inverted > 0))
        if len(coords) < 10:
            return gray_image, 0.0

        angle = cv2.minAreaRect(coords)[-1]
        # Adjust angle format from OpenCV minAreaRect
        if angle < -45:
            angle = -(90 + angle)
        elif angle > 45:
            angle = 90 - angle

        # Only correct noticeable skew (e.g. between 0.5 and 45 degrees)
        if abs(angle) < 0.5:
            return gray_image, 0.0

        (h, w) = gray_image.shape[:2]
        center = (w // 2, h // 2)
        m = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            gray_image, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return rotated, angle

    @classmethod
    def preprocess_for_ocr(cls, image_path_or_bytes) -> Tuple[np.ndarray, float]:
        """Runs the standard preprocessing pipeline (Grayscale -> Denoise -> Deskew -> Binarize)."""
        img = cls.load_image(image_path_or_bytes)
        gray = cls.to_grayscale(img)
        denoised = cls.remove_noise(gray)
        deskewed, angle = cls.deskew(denoised)
        binarized = cls.binarize_otsu(deskewed)
        return binarized, angle
