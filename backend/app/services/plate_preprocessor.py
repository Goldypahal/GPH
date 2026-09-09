from typing import Optional, Tuple
import numpy as np

class PlatePreprocessor:
    """
    Stage 3 License Plate Image Preprocessor.
    Performs geometric deskewing, CLAHE illumination correction (night glare / shadows),
    and edge-preserving binarization prior to feeding crops into OCR engines.
    """

    @staticmethod
    def deskew_plate(plate_img: np.ndarray) -> np.ndarray:
        """Rotates skewed license plate to a horizontal baseline using contour orientation."""
        try:
            import cv2
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            coords = np.column_stack(np.where(thresh > 0))
            if len(coords) < 50:
                return plate_img

            angle = cv2.minAreaRect(coords)[-1]
            # Normalization of OpenCV minAreaRect angle
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            # Only correct realistic skew angles (-25 to 25 degrees)
            if abs(angle) > 1.5 and abs(angle) < 25.0:
                h, w = plate_img.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                rotated = cv2.warpAffine(plate_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
                return rotated
        except Exception:
            pass
        return plate_img

    @staticmethod
    def enhance_contrast_clahe(plate_img: np.ndarray) -> np.ndarray:
        """
        Applies Contrast Limited Adaptive Histogram Equalization in LAB space.
        Pierces headlight glare, deep shadows, and rainy blur.
        """
        try:
            import cv2
            lab = cv2.cvtColor(plate_img, cv2.COLOR_BGR2LAB)
            l_chan, a_chan, b_chan = cv2.split(lab)

            clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
            cl = clahe.apply(l_chan)

            merged = cv2.merge((cl, a_chan, b_chan))
            enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
            return enhanced
        except Exception:
            return plate_img

    @classmethod
    def preprocess(cls, plate_img: np.ndarray, target_height: int = 64) -> np.ndarray:
        """
        Full preprocessing pipeline:
        1. Scale to optimal OCR height (preserving aspect ratio)
        2. Geometric deskewing
        3. CLAHE contrast equalization
        """
        if plate_img is None or plate_img.size == 0:
            return plate_img

        # 1. Scale up small crops so characters are distinctly readable
        try:
            import cv2
            h, w = plate_img.shape[:2]
            if h < target_height:
                scale = target_height / float(h)
                new_w = max(1, int(w * scale))
                plate_img = cv2.resize(plate_img, (new_w, target_height), interpolation=cv2.INTER_CUBIC)
        except Exception:
            try:
                from PIL import Image
                h, w = plate_img.shape[:2]
                if h < target_height:
                    scale = target_height / float(h)
                    new_w = max(1, int(w * scale))
                    pil_img = Image.fromarray(plate_img)
                    resized = pil_img.resize((new_w, target_height), Image.Resampling.BICUBIC)
                    plate_img = np.array(resized)
            except Exception:
                pass

        # 2. Deskew
        aligned = cls.deskew_plate(plate_img)

        # 3. Contrast enhancement
        enhanced = cls.enhance_contrast_clahe(aligned)

        return enhanced

plate_preprocessor = PlatePreprocessor()
