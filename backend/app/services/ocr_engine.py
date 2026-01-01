"""Multi-Pass OCR Engine for SMELens

Implements an intelligent OCR system using Tesseract with:
- Multiple OCR passes with different configurations
- Adaptive PSM modes for different document types
- LSTM neural network mode (OEM 1)
- Per-word confidence tracking
"""
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


class PSMMode(Enum):
    """Tesseract Page Segmentation Modes for different document types."""
    AUTO = 3           # Fully automatic page segmentation
    SINGLE_COLUMN = 4  # Single column of text (receipts)
    SINGLE_BLOCK = 6   # Single uniform block of text
    SINGLE_LINE = 7    # Single text line
    WORD = 8           # Single word
    SPARSE_TEXT = 11   # Sparse text, find as much text as possible
    SPARSE_OSD = 12    # Sparse text with OSD


class OEMMode(Enum):
    """Tesseract OCR Engine Modes."""
    LEGACY = 0         # Legacy engine only
    LSTM = 1           # Neural network LSTM engine only
    COMBINED = 2       # Legacy + LSTM
    DEFAULT = 3        # Default based on availability


@dataclass
class OCRWord:
    """Represents a single word detected by OCR with metadata."""
    text: str
    confidence: float  # 0-100 from Tesseract
    left: int
    top: int
    width: int
    height: int
    block_num: int
    line_num: int
    word_num: int


@dataclass
class OCRPassResult:
    """Result from a single OCR pass."""
    text: str
    words: list[OCRWord]
    config_used: str
    average_confidence: float
    word_count: int


@dataclass
class MultiPassOCRResult:
    """Combined result from multiple OCR passes."""
    primary_text: str
    all_passes: list[OCRPassResult]
    merged_text: str
    best_confidence: float
    word_confidences: dict[str, float]  # word -> confidence
    low_confidence_words: list[str]
    numbers_detected: list[str]
    config_summary: str


class MultiPassOCREngine:
    """
    Multi-pass OCR engine with adaptive configuration.
    
    Runs multiple OCR passes with different settings to maximize
    accuracy, especially for handwritten and numeric content.
    """
    
    # Tesseract configuration templates
    CONFIGS = {
        "general": {
            "oem": OEMMode.LSTM.value,
            "psm": PSMMode.SINGLE_BLOCK.value,
            "extra": "",
            "description": "General text extraction"
        },
        "receipt": {
            "oem": OEMMode.LSTM.value,
            "psm": PSMMode.SINGLE_COLUMN.value,
            "extra": "",
            "description": "Receipt/vertical document"
        },
        "numbers": {
            "oem": OEMMode.LSTM.value,
            "psm": PSMMode.SINGLE_BLOCK.value,
            "extra": "-c tessedit_char_whitelist=0123456789.,$/€£¥KES ",
            "description": "Numbers and currency focused"
        },
        "sparse": {
            "oem": OEMMode.LSTM.value,
            "psm": PSMMode.SPARSE_TEXT.value,
            "extra": "",
            "description": "Sparse/handwritten text"
        },
    }
    
    # Confidence thresholds
    LOW_CONFIDENCE_THRESHOLD: float = 60.0
    HIGH_CONFIDENCE_THRESHOLD: float = 85.0
    
    def __init__(self, lang: str = "eng"):
        """
        Initialize OCR engine.
        
        Args:
            lang: Tesseract language code (default: English)
        """
        self.lang = lang
        self._verify_tesseract()
    
    def _verify_tesseract(self) -> None:
        """Verify Tesseract is installed and accessible."""
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"OCR Engine: Tesseract {version} initialized")
        except Exception as e:
            logger.error(f"OCR Engine: Tesseract not found - {e}")
            raise RuntimeError("Tesseract OCR is not installed or not in PATH")
    
    def _build_config(self, config_name: str) -> str:
        """Build Tesseract config string."""
        cfg = self.CONFIGS.get(config_name, self.CONFIGS["general"])
        config_str = f"--oem {cfg['oem']} --psm {cfg['psm']}"
        if cfg["extra"]:
            config_str += f" {cfg['extra']}"
        return config_str
    
    def _run_single_pass(
        self, 
        image: Image.Image, 
        config_name: str
    ) -> OCRPassResult:
        """
        Run a single OCR pass with specific configuration.
        
        Args:
            image: PIL Image to process
            config_name: Name of configuration to use
            
        Returns:
            OCRPassResult with extracted text and metadata
        """
        config_str = self._build_config(config_name)
        cfg_info = self.CONFIGS.get(config_name, {})
        
        logger.info(f"OCR Pass [{config_name}]: {cfg_info.get('description', 'Custom')}")
        
        # Get detailed OCR data with word-level info
        try:
            ocr_data = pytesseract.image_to_data(
                image, 
                lang=self.lang,
                config=config_str,
                output_type=pytesseract.Output.DICT
            )
        except Exception as e:
            logger.error(f"OCR Pass [{config_name}]: Failed - {e}")
            return OCRPassResult(
                text="",
                words=[],
                config_used=config_str,
                average_confidence=0.0,
                word_count=0
            )
        
        # Extract words with confidence
        words: list[OCRWord] = []
        confidences: list[float] = []
        
        n_boxes = len(ocr_data["text"])
        for i in range(n_boxes):
            text = ocr_data["text"][i].strip()
            conf = ocr_data["conf"][i]
            
            # Skip empty results or invalid confidence
            if not text or conf == -1:
                continue
            
            conf_float = float(conf)
            confidences.append(conf_float)
            
            words.append(OCRWord(
                text=text,
                confidence=conf_float,
                left=ocr_data["left"][i],
                top=ocr_data["top"][i],
                width=ocr_data["width"][i],
                height=ocr_data["height"][i],
                block_num=ocr_data["block_num"][i],
                line_num=ocr_data["line_num"][i],
                word_num=ocr_data["word_num"][i]
            ))
        
        # Build full text
        full_text = pytesseract.image_to_string(
            image,
            lang=self.lang,
            config=config_str
        )
        
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
        
        logger.info(f"OCR Pass [{config_name}]: {len(words)} words, avg confidence {avg_conf:.1f}%")
        
        return OCRPassResult(
            text=full_text.strip(),
            words=words,
            config_used=config_str,
            average_confidence=avg_conf,
            word_count=len(words)
        )
    
    def run_multi_pass(
        self, 
        image: Image.Image,
        document_hint: str = "unknown"
    ) -> MultiPassOCRResult:
        """
        Run multiple OCR passes and merge results.
        
        Strategy:
        1. Run general pass for baseline
        2. Run document-specific pass if hint provided
        3. Run numbers-focused pass
        4. Merge results, preferring higher confidence
        
        Args:
            image: PIL Image to process
            document_hint: Hint about document type
            
        Returns:
            MultiPassOCRResult with merged output
        """
        logger.info(f"Multi-Pass OCR: Starting with hint='{document_hint}'")
        
        passes: list[OCRPassResult] = []
        
        # Pass 1: General text extraction
        general_result = self._run_single_pass(image, "general")
        passes.append(general_result)
        
        # Pass 2: Document-specific (if applicable)
        if document_hint in ["receipt", "invoice"]:
            receipt_result = self._run_single_pass(image, "receipt")
            passes.append(receipt_result)
        elif document_hint == "handwritten":
            sparse_result = self._run_single_pass(image, "sparse")
            passes.append(sparse_result)
        
        # Pass 3: Numbers-focused pass
        numbers_result = self._run_single_pass(image, "numbers")
        passes.append(numbers_result)
        
        # Merge results
        merged = self._merge_passes(passes)
        
        return merged
    
    def _merge_passes(self, passes: list[OCRPassResult]) -> MultiPassOCRResult:
        """
        Merge results from multiple OCR passes.
        
        Uses confidence-weighted merging for ambiguous words.
        """
        if not passes:
            return MultiPassOCRResult(
                primary_text="",
                all_passes=[],
                merged_text="",
                best_confidence=0.0,
                word_confidences={},
                low_confidence_words=[],
                numbers_detected=[],
                config_summary="no passes"
            )
        
        # Use the pass with highest average confidence as primary
        best_pass = max(passes, key=lambda p: p.average_confidence)
        primary_text = best_pass.text
        
        # Collect word confidences from all passes
        word_confidences: dict[str, float] = {}
        for pass_result in passes:
            for word in pass_result.words:
                key = word.text.lower()
                if key not in word_confidences or word.confidence > word_confidences[key]:
                    word_confidences[key] = word.confidence
        
        # Find low confidence words
        low_conf_words = [
            word for word, conf in word_confidences.items()
            if conf < self.LOW_CONFIDENCE_THRESHOLD
        ]
        
        # Extract numbers from numbers-focused pass
        numbers: list[str] = []
        for pass_result in passes:
            if "whitelist" in pass_result.config_used:
                for word in pass_result.words:
                    # Check if word contains digits
                    if any(c.isdigit() for c in word.text):
                        numbers.append(word.text)
        
        # If no numbers from focused pass, extract from general
        if not numbers:
            import re
            for pass_result in passes:
                found = re.findall(r'[\d.,]+', pass_result.text)
                numbers.extend(found)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_numbers = []
        for n in numbers:
            if n not in seen:
                seen.add(n)
                unique_numbers.append(n)
        
        # Build config summary
        configs_used = [p.config_used.split("--")[1][:20] for p in passes]
        config_summary = f"{len(passes)} passes: {', '.join(configs_used)}"
        
        return MultiPassOCRResult(
            primary_text=primary_text,
            all_passes=passes,
            merged_text=primary_text,  # Could enhance with word-level merging
            best_confidence=best_pass.average_confidence,
            word_confidences=word_confidences,
            low_confidence_words=low_conf_words,
            numbers_detected=unique_numbers,
            config_summary=config_summary
        )


def run_ocr(
    image: Image.Image, 
    document_type: str = "unknown",
    lang: str = "eng"
) -> MultiPassOCRResult:
    """
    Convenience function to run multi-pass OCR on an image.
    
    Args:
        image: PIL Image to process
        document_type: Hint about document type
        lang: Tesseract language code
        
    Returns:
        MultiPassOCRResult with comprehensive OCR output
    """
    engine = MultiPassOCREngine(lang=lang)
    return engine.run_multi_pass(image, document_hint=document_type)
