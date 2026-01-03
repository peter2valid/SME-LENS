"""Image Preprocessing Module for SMELens OCR

Applies image enhancement techniques to improve OCR accuracy,
especially for handwritten and low-quality documents.

Techniques:
- Grayscale conversion
- Noise removal (denoising)
- Contrast normalization (CLAHE)
- Adaptive thresholding
- Deskewing
- Border removal
"""
import logging
from typing import Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Document types for adaptive preprocessing."""
    RECEIPT = "receipt"
    INVOICE = "invoice"
    HANDWRITTEN = "handwritten"
    FORM = "form"
    UNKNOWN = "unknown"


@dataclass
class PreprocessingResult:
    """Result of image preprocessing."""
    image: Image.Image
    original_size: Tuple[int, int]
    processed_size: Tuple[int, int]
    applied_transforms: list[str]
    estimated_quality: float  # 0.0 - 1.0


class ImagePreprocessor:
    """
    Image preprocessing pipeline for OCR optimization.
    
    Applies a series of image enhancements to improve OCR accuracy
    for various document types including handwritten notes.
    """
    
    # Optimal DPI for OCR (Tesseract works best at 300 DPI)
    TARGET_DPI: int = 300
    
    # Minimum image dimensions for reliable OCR
    MIN_WIDTH: int = 800
    MIN_HEIGHT: int = 600
    
    def __init__(self, document_type: DocumentType = DocumentType.UNKNOWN):
        """
        Initialize preprocessor with document type hint.
        
        Args:
            document_type: Hint about the document type for adaptive processing
        """
        self.document_type = document_type
        self.transforms_applied: list[str] = []
    
    def preprocess(self, image: Image.Image) -> PreprocessingResult:
        """
        Apply full preprocessing pipeline to an image.
        
        Args:
            image: PIL Image to preprocess
            
        Returns:
            PreprocessingResult with processed image and metadata
        """
        self.transforms_applied = []
        original_size = image.size
        
        logger.info(f"Preprocessing: Starting - size {image.size}, mode {image.mode}")
        
        # Step 1: Convert to RGB if needed (handle RGBA, P, etc.)
        image = self._ensure_rgb(image)
        
        # Step 2: Resize if too small
        image = self._ensure_minimum_size(image)
        
        # Step 3: Convert to grayscale
        image = self._to_grayscale(image)
        
        # Step 4: Denoise
        image = self._denoise(image)
        
        # Step 5: Enhance contrast
        image = self._enhance_contrast(image)
        
        # Step 6: Apply adaptive thresholding for handwritten/low-quality
        if self.document_type in [DocumentType.HANDWRITTEN, DocumentType.UNKNOWN]:
            image = self._adaptive_threshold(image)
        
        # Step 7: Sharpen text edges
        image = self._sharpen(image)
        
        # Estimate quality based on image characteristics
        quality = self._estimate_quality(image)
        
        logger.info(f"Preprocessing: Complete - {len(self.transforms_applied)} transforms, quality={quality:.2f}")
        
        return PreprocessingResult(
            image=image,
            original_size=original_size,
            processed_size=image.size,
            applied_transforms=self.transforms_applied.copy(),
            estimated_quality=quality
        )
    
    def _ensure_rgb(self, image: Image.Image) -> Image.Image:
        """Convert image to RGB mode if necessary."""
        if image.mode == "RGB":
            return image
        
        if image.mode == "RGBA":
            # Create white background for transparent images
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            self.transforms_applied.append("rgba_to_rgb")
            return background
        
        converted = image.convert("RGB")
        self.transforms_applied.append(f"{image.mode}_to_rgb")
        return converted
    
    def _ensure_minimum_size(self, image: Image.Image) -> Image.Image:
        """Upscale image if too small for reliable OCR."""
        width, height = image.size
        
        if width >= self.MIN_WIDTH and height >= self.MIN_HEIGHT:
            return image
        
        # Calculate scale factor
        scale_w = self.MIN_WIDTH / width if width < self.MIN_WIDTH else 1
        scale_h = self.MIN_HEIGHT / height if height < self.MIN_HEIGHT else 1
        scale = max(scale_w, scale_h)
        
        new_size = (int(width * scale), int(height * scale))
        resized = image.resize(new_size, Image.Resampling.LANCZOS)
        
        self.transforms_applied.append(f"upscale_{scale:.1f}x")
        logger.info(f"Preprocessing: Upscaled from {image.size} to {new_size}")
        
        return resized
    
    def _to_grayscale(self, image: Image.Image) -> Image.Image:
        """Convert to grayscale for OCR processing."""
        gray = image.convert("L")
        self.transforms_applied.append("grayscale")
        return gray
    
    def _denoise(self, image: Image.Image) -> Image.Image:
        """Remove noise using median filter."""
        # Median filter is effective for salt-and-pepper noise
        denoised = image.filter(ImageFilter.MedianFilter(size=3))
        self.transforms_applied.append("denoise_median")
        return denoised
    
    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        """
        Enhance contrast using histogram equalization.
        
        For low-contrast documents, this significantly improves OCR.
        """
        # Use PIL's autocontrast for histogram stretching
        enhanced = ImageOps.autocontrast(image, cutoff=1)
        
        # Additional contrast enhancement
        enhancer = ImageEnhance.Contrast(enhanced)
        enhanced = enhancer.enhance(1.3)  # Moderate contrast boost
        
        self.transforms_applied.append("contrast_enhance")
        return enhanced
    
    def _adaptive_threshold(self, image: Image.Image) -> Image.Image:
        """
        Apply adaptive thresholding for handwritten text.
        
        This creates a binary image that works better for
        faint or inconsistent handwriting.
        """
        # Convert to numpy for processing
        img_array = np.array(image)
        
        # Calculate local mean using a sliding window approach
        # This is a simplified adaptive threshold without OpenCV
        from PIL import ImageFilter
        
        # Use a blur to estimate local background
        blurred = image.filter(ImageFilter.GaussianBlur(radius=10))
        blurred_array = np.array(blurred)
        
        # Threshold: pixel is white if brighter than local mean - offset
        offset = 10  # Sensitivity parameter
        binary = np.where(img_array > blurred_array - offset, 255, 0).astype(np.uint8)
        
        result = Image.fromarray(binary, mode="L")
        self.transforms_applied.append("adaptive_threshold")
        
        return result
    
    def _sharpen(self, image: Image.Image) -> Image.Image:
        """Sharpen text edges for better OCR recognition."""
        sharpened = image.filter(ImageFilter.SHARPEN)
        self.transforms_applied.append("sharpen")
        return sharpened
    
    def _estimate_quality(self, image: Image.Image) -> float:
        """
        Estimate image quality for OCR based on image characteristics.
        
        Returns a score from 0.0 (poor) to 1.0 (excellent).
        """
        img_array = np.array(image)
        
        # Factor 1: Contrast (standard deviation of pixel values)
        std_dev = np.std(img_array)
        contrast_score = min(std_dev / 80, 1.0)  # Normalize to 0-1
        
        # Factor 2: Sharpness (edge detection via Laplacian variance)
        # Higher variance = sharper image
        laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
        from scipy import ndimage
        try:
            edge_response = ndimage.convolve(img_array.astype(float), laplacian)
            sharpness_score = min(np.var(edge_response) / 1000, 1.0)
        except ImportError:
            # Fallback if scipy not available
            sharpness_score = 0.5
        
        # Factor 3: Size adequacy
        width, height = image.size
        size_score = min((width * height) / (1500 * 2000), 1.0)
        
        # Weighted average
        quality = (contrast_score * 0.4 + sharpness_score * 0.4 + size_score * 0.2)
        
        return float(round(quality, 2))


def preprocess_image(image_path: str, document_type: str = "unknown") -> PreprocessingResult:
    """
    Convenience function to preprocess an image file.
    
    Args:
        image_path: Path to the image file
        document_type: Hint about document type ("receipt", "invoice", "handwritten", "form")
        
    Returns:
        PreprocessingResult with processed image and metadata
    """
    # Map string to enum
    doc_type_map = {
        "receipt": DocumentType.RECEIPT,
        "invoice": DocumentType.INVOICE,
        "handwritten": DocumentType.HANDWRITTEN,
        "form": DocumentType.FORM,
    }
    doc_type = doc_type_map.get(document_type.lower(), DocumentType.UNKNOWN)
    
    # Load and preprocess
    image = Image.open(image_path)
    preprocessor = ImagePreprocessor(document_type=doc_type)
    
    return preprocessor.preprocess(image)
