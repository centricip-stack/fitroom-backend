"""
SkinAnalyzerService
--------------------
Detects a face using OpenCV's Haar cascade face detector, crops the face region,
and classifies skin tone into 5 categories (Light / Light-Medium / Medium / Tan / Deep)
using Luma-based perceived brightness analysis.
"""

import logging
from pathlib import Path

import cv2
import numpy as np
from fastapi import HTTPException

# For fallback data path
import cv2.data

from app.config.color_rules import (
    COLOR_RULES,
    SKIN_HSV_FILTER,
    SKIN_TONE_THRESHOLDS,
    SkinTone,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Haar cascade path
# ---------------------------------------------------------------------------
_CASCADE_PATH = str(
    Path(cv2.__file__).parent / "data" / "haarcascade_frontalface_default.xml"
)


class SkinAnalyzerService:
    """
    Encapsulates face detection and accurate skin-tone analysis.
    """

    def __init__(self) -> None:
        self._face_detector = cv2.CascadeClassifier(_CASCADE_PATH)
        
        if self._face_detector.empty():
            logger.warning("Haar cascade not found at %s, trying cv2.data fallback", _CASCADE_PATH)
            fallback_path = str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
            self._face_detector = cv2.CascadeClassifier(fallback_path)

        if self._face_detector.empty():
            raise RuntimeError("Could not load OpenCV Haar cascade face detector.")
            
        logger.info("SkinAnalyzerService initialised.")

    def analyze(self, image_bytes: bytes) -> tuple[SkinTone, list[str]]:
        """
        Analyze skin tone from raw image bytes and return the tone + color palette.
        """
        img_rgb = self._decode_image(image_bytes)
        face_crop = self._extract_face(img_rgb)
        skin_tone = self._classify_tone(face_crop)
        recommended_colors = COLOR_RULES.get(skin_tone, COLOR_RULES[SkinTone.UNKNOWN])
        
        logger.info("Detected Skin Tone: %s", skin_tone)
        return skin_tone, recommended_colors

    def _decode_image(self, image_bytes: bytes) -> np.ndarray:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            raise HTTPException(status_code=422, detail="Invalid image file.")
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    def _extract_face(self, img_rgb: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        
        # Optimized for small/moderate resolution images
        faces = self._face_detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 30)
        )

        if len(faces) == 0:
            logger.warning("Face detection failed; using center crop as fallback.")
            h, w, _ = img_rgb.shape
            # Return center 50%
            return img_rgb[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4]

        # Use largest face
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        
        # Crop slightly inward to avoid hair/background (10% margin)
        mh, mw = int(h * 0.1), int(w * 0.1)
        face_crop = img_rgb[y + mh : y + h - mh, x + mw : x + w - mw]
        
        return face_crop

    def _classify_tone(self, face_crop: np.ndarray) -> SkinTone:
        """
        Classify skin tone using perceived brightness (Luma).
        """
        hsv = cv2.cvtColor(face_crop, cv2.COLOR_RGB2HSV)
        h_ch, s_ch, v_ch = cv2.split(hsv)

        f = SKIN_HSV_FILTER
        t = SKIN_TONE_THRESHOLDS

        # Standard skin detection ranges in HSV
        skin_mask = (
            (s_ch > f["saturation_min"])
            & (s_ch < f["saturation_max"])
            & (v_ch > f["value_min"])
            & (v_ch < f["value_max"])
        )
        skin_pixels = face_crop[skin_mask]

        if len(skin_pixels) == 0:
            # Fallback to full crop if mask filter is too strict
            avg_rgb_vals = np.mean(face_crop, axis=(0,1))
            avg_luma = 0.299 * avg_rgb_vals[0] + 0.587 * avg_rgb_vals[1] + 0.114 * avg_rgb_vals[2]
            logger.warning("No skin pixels found; using full crop luma: %.2f", avg_luma)
        else:
            # perceived brightness logic
            luma = (
                0.299 * skin_pixels[:, 0] + 
                0.587 * skin_pixels[:, 1] + 
                0.114 * skin_pixels[:, 2]
            )
            avg_luma = float(np.mean(luma))
        
        logger.info("Calculated Skin Luma: %.2f", avg_luma)

        if avg_luma > t["LIGHT_MIN"]:
            return SkinTone.LIGHT
        elif avg_luma > t["LIGHT_MEDIUM_MIN"]:
            return SkinTone.LIGHT_MEDIUM
        elif avg_luma > t["MEDIUM_MIN"]:
            return SkinTone.MEDIUM
        elif avg_luma > t["TAN_MIN"]:
            return SkinTone.TAN
        else:
            return SkinTone.DEEP
