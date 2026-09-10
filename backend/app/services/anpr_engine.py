import re
from typing import Dict, Any, Tuple, Optional

# Indian State & UT Codes
VALID_STATE_CODES = {
    "GJ", "MH", "RJ", "MP", "DL", "KA", "TN", "UP", "HR", "PB",
    "AP", "TS", "KL", "WB", "BR", "OD", "AS", "GA", "CH", "JK", "BH"
}

# Optical Character Recognition Disambiguation Map
CHAR_DISAMBIGUATION = {
    # If in alphabetic position:
    "ALPHA": {
        "0": "O", "1": "I", "2": "Z", "5": "S", "8": "B", "6": "G"
    },
    # If in numeric position:
    "NUMERIC": {
        "O": "0", "I": "1", "Z": "2", "S": "5", "B": "8", "G": "6", "D": "0"
    }
}

class ANPREngine:
    """
    Production-grade Indian Automatic Number Plate Recognition (ANPR)
    Normalization, Validation, and Confidence Scoring Engine.
    """

    @staticmethod
    def normalize_plate(raw_text: str) -> str:
        """
        Removes delimiters, whitespaces, IND country codes, and non-alphanumerics.
        Example: 'GJ-01-AB-1234' -> 'GJ01AB1234'
        """
        if not raw_text:
            return ""
        
        cleaned = re.sub(r'[^A-Za-z0-9]', '', raw_text).upper()
        # Remove leading 'IND' stamp if detected as characters by OCR
        if cleaned.startswith("IND") and len(cleaned) > 8:
            cleaned = cleaned[3:]
            
        return cleaned

    @classmethod
    def validate_and_correct(cls, raw_text: str) -> Tuple[str, float, bool]:
        """
        Applies positional regex and optical heuristic corrections.
        Returns: (corrected_plate, confidence_score, is_valid_format)
        """
        normalized = cls.normalize_plate(raw_text)
        if len(normalized) < 8 or len(normalized) > 11:
            return normalized, 0.50, False

        # Pattern 1: Standard Indian Plate - 2 Letters, 2 Digits, 1-3 Letters, 4 Digits
        # Example: GJ01AB1234 or GJ06X1234 or GJ18AAA9999
        match = re.match(r'^([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{4})$', normalized)
        if match:
            state, rto, series, number = match.groups()
            conf = 0.96 if state in VALID_STATE_CODES else 0.82
            return f"{state}{rto.zfill(2)}{series}{number}", conf, True

        # Pattern 2: Bharat Series (BH) - 2 Digits, BH, 4 Digits, 2 Letters
        # Example: 22BH1234AA
        bh_match = re.match(r'^(\d{2})BH(\d{4})([A-Z]{2})$', normalized)
        if bh_match:
            return normalized, 0.95, True

        # Heuristic Auto-Correction for Common OCR Misreads
        corrected = list(normalized)
        # Position 0 & 1 must be State letters
        for i in [0, 1]:
            if i < len(corrected) and corrected[i] in CHAR_DISAMBIGUATION["ALPHA"]:
                corrected[i] = CHAR_DISAMBIGUATION["ALPHA"][corrected[i]]
                
        # Position 2 & 3 must be RTO numbers
        for i in [2, 3]:
            if i < len(corrected) and corrected[i] in CHAR_DISAMBIGUATION["NUMERIC"]:
                corrected[i] = CHAR_DISAMBIGUATION["NUMERIC"][corrected[i]]
                
        candidate = "".join(corrected)
        retry_match = re.match(r'^([A-Z]{2})(\d{1,2})([A-Z]{1,3})(\d{4})$', candidate)
        if retry_match:
            state, rto, series, number = retry_match.groups()
            return f"{state}{rto.zfill(2)}{series}{number}", 0.88, True

        return normalized, 0.65, False

    @staticmethod
    def calculate_levenshtein(s1: str, s2: str) -> int:
        """Calculates edit distance between two plate strings."""
        if len(s1) < len(s2):
            return ANPREngine.calculate_levenshtein(s2, s1)
        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]


    def process_frame(
        self,
        raw_frame: Any = None,
        camera_id: str = "CAM-01",
        synthetic_plate: Optional[str] = None
    ) -> Tuple[str, float, str, str]:
        """
        High-level ANPR processing helper.
        Returns: (plate_text, ocr_confidence, vehicle_type, vehicle_color)
        """
        from backend.app.core.config import settings
        if synthetic_plate:
            corrected, conf, _ = self.validate_and_correct(synthetic_plate)
            return corrected, conf, "SUV", "Gold"

        if settings.ENVIRONMENT == "production":
            return "", 0.0, "Unknown", "Unknown"

        plate_candidate = "GJ01AB1234"
        corrected, conf, _ = self.validate_and_correct(plate_candidate)
        return corrected, conf, "SUV", "Gold"


anpr_engine = ANPREngine()

