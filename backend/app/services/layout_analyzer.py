"""Layout-Aware Extraction Engine for SMELens

Extraction that uses text position and document structure,
not just raw text strings.

Implements:
- Bounding-box awareness from OCR
- Page zones (header 15%, body, footer 20%)
- Table detection (rows + columns)
- Font size / line prominence heuristics

Layout Rules:
- Vendor names usually appear in header zone
- Totals usually appear in footer zone
- Identifiers often appear near labels
- Tables have aligned columns

This logic works even when OCR text is imperfect.
"""
import re
import logging
from typing import Optional, Any, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class Zone(Enum):
    """Document zones based on vertical position."""
    HEADER = "header"   # Top 15%
    BODY = "body"       # Middle 65%
    FOOTER = "footer"   # Bottom 20%


class Alignment(Enum):
    """Text alignment within a line."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    UNKNOWN = "unknown"


@dataclass
class BoundingBox:
    """Bounding box for a text element."""
    left: int
    top: int
    width: int
    height: int
    
    @property
    def right(self) -> int:
        return self.left + self.width
    
    @property
    def bottom(self) -> int:
        return self.top + self.height
    
    @property
    def center_x(self) -> int:
        return self.left + self.width // 2
    
    @property
    def center_y(self) -> int:
        return self.top + self.height // 2
    
    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass
class LayoutWord:
    """A word with layout information."""
    text: str
    bbox: BoundingBox
    confidence: float
    line_num: int
    word_num: int
    block_num: int
    zone: Zone = Zone.BODY
    is_bold: bool = False  # Inferred from size
    relative_size: float = 1.0  # Relative to median


@dataclass
class LayoutLine:
    """A line of text with layout information."""
    words: list[LayoutWord]
    bbox: BoundingBox
    line_num: int
    zone: Zone
    alignment: Alignment
    text: str
    average_word_height: float
    is_prominent: bool = False  # Larger than average


@dataclass
class TableCell:
    """A cell in a detected table."""
    text: str
    row: int
    col: int
    bbox: BoundingBox
    is_header: bool = False


@dataclass
class DetectedTable:
    """A detected table structure."""
    cells: list[TableCell]
    rows: int
    cols: int
    bbox: BoundingBox
    headers: list[str]


@dataclass
class LayoutAnalysisResult:
    """Complete layout analysis result."""
    # Document dimensions
    page_width: int
    page_height: int
    
    # Zones
    header_zone: tuple[int, int]  # (top, bottom)
    body_zone: tuple[int, int]
    footer_zone: tuple[int, int]
    
    # Elements
    lines: list[LayoutLine]
    tables: list[DetectedTable]
    
    # Prominent elements
    header_lines: list[LayoutLine]
    footer_lines: list[LayoutLine]
    prominent_lines: list[LayoutLine]
    
    # Statistics
    median_line_height: float
    total_lines: int
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "page_dimensions": {
                "width": self.page_width,
                "height": self.page_height
            },
            "zones": {
                "header": {"top": self.header_zone[0], "bottom": self.header_zone[1]},
                "body": {"top": self.body_zone[0], "bottom": self.body_zone[1]},
                "footer": {"top": self.footer_zone[0], "bottom": self.footer_zone[1]}
            },
            "statistics": {
                "total_lines": self.total_lines,
                "header_lines": len(self.header_lines),
                "footer_lines": len(self.footer_lines),
                "prominent_lines": len(self.prominent_lines),
                "tables_detected": len(self.tables)
            }
        }


class LayoutAnalyzer:
    """
    Analyzes document layout for intelligent extraction.
    
    Uses spatial information from OCR to understand document
    structure beyond raw text.
    """
    
    # Zone boundaries (percentage of page height)
    HEADER_ZONE_PERCENT = 0.15
    FOOTER_ZONE_PERCENT = 0.80
    
    # Prominence threshold (relative to median)
    PROMINENCE_THRESHOLD = 1.3
    
    # Table detection thresholds
    MIN_TABLE_COLUMNS = 2
    MIN_TABLE_ROWS = 2
    COLUMN_ALIGNMENT_TOLERANCE = 20  # pixels
    
    def __init__(self):
        """Initialize the layout analyzer."""
        self.words: list[LayoutWord] = []
        self.page_width: int = 0
        self.page_height: int = 0
    
    def analyze(
        self,
        ocr_words: list[dict],
        page_width: int = 0,
        page_height: int = 0
    ) -> LayoutAnalysisResult:
        """
        Analyze document layout from OCR word data.
        
        Args:
            ocr_words: List of word dictionaries with bbox info
                       Each dict should have: text, left, top, width, height, 
                       confidence, line_num, word_num, block_num
            page_width: Page width (0 = infer from content)
            page_height: Page height (0 = infer from content)
            
        Returns:
            LayoutAnalysisResult with complete layout information
        """
        logger.info(f"LayoutAnalyzer: Analyzing {len(ocr_words)} words")
        
        # Convert to LayoutWord objects
        self.words = self._convert_words(ocr_words)
        
        if not self.words:
            return self._empty_result()
        
        # Infer page dimensions if not provided
        if page_width == 0:
            page_width = max(w.bbox.right for w in self.words) + 20
        if page_height == 0:
            page_height = max(w.bbox.bottom for w in self.words) + 20
        
        self.page_width = page_width
        self.page_height = page_height
        
        # Calculate zone boundaries
        header_end = int(page_height * self.HEADER_ZONE_PERCENT)
        footer_start = int(page_height * self.FOOTER_ZONE_PERCENT)
        
        # Assign zones to words
        for word in self.words:
            word.zone = self._get_zone(word.bbox.center_y, header_end, footer_start)
        
        # Group words into lines
        lines = self._group_into_lines()
        
        # Calculate median line height
        heights = [line.average_word_height for line in lines]
        median_height = sorted(heights)[len(heights) // 2] if heights else 20
        
        # Mark prominent lines
        for line in lines:
            if line.average_word_height > median_height * self.PROMINENCE_THRESHOLD:
                line.is_prominent = True
        
        # Detect tables
        tables = self._detect_tables(lines)
        
        # Categorize lines
        header_lines = [l for l in lines if l.zone == Zone.HEADER]
        footer_lines = [l for l in lines if l.zone == Zone.FOOTER]
        prominent_lines = [l for l in lines if l.is_prominent]
        
        logger.info(f"LayoutAnalyzer: Found {len(lines)} lines, "
                   f"{len(header_lines)} in header, {len(footer_lines)} in footer, "
                   f"{len(tables)} tables")
        
        return LayoutAnalysisResult(
            page_width=page_width,
            page_height=page_height,
            header_zone=(0, header_end),
            body_zone=(header_end, footer_start),
            footer_zone=(footer_start, page_height),
            lines=lines,
            tables=tables,
            header_lines=header_lines,
            footer_lines=footer_lines,
            prominent_lines=prominent_lines,
            median_line_height=median_height,
            total_lines=len(lines)
        )
    
    def analyze_from_text(
        self,
        text: str,
        simulate_bbox: bool = True
    ) -> LayoutAnalysisResult:
        """
        Analyze layout from plain text (simulating bounding boxes).
        
        This is a fallback when full OCR bbox data is not available.
        Uses line-based heuristics instead of precise positions.
        
        Args:
            text: Plain text from OCR
            simulate_bbox: Whether to create simulated bboxes
            
        Returns:
            LayoutAnalysisResult
        """
        lines = text.split('\n')
        ocr_words = []
        
        y_position = 10
        line_height = 20
        char_width = 8
        
        for line_num, line in enumerate(lines):
            words = line.split()
            x_position = 10
            
            for word_num, word in enumerate(words):
                word_width = len(word) * char_width
                
                ocr_words.append({
                    'text': word,
                    'left': x_position,
                    'top': y_position,
                    'width': word_width,
                    'height': line_height,
                    'confidence': 80.0,
                    'line_num': line_num,
                    'word_num': word_num,
                    'block_num': 0
                })
                
                x_position += word_width + char_width
            
            y_position += line_height + 5
        
        return self.analyze(
            ocr_words,
            page_width=800,
            page_height=y_position + 20
        )
    
    def _convert_words(self, ocr_words: list[dict]) -> list[LayoutWord]:
        """Convert OCR word dictionaries to LayoutWord objects."""
        result = []
        
        for w in ocr_words:
            try:
                bbox = BoundingBox(
                    left=int(w.get('left', 0)),
                    top=int(w.get('top', 0)),
                    width=int(w.get('width', 0)),
                    height=int(w.get('height', 0))
                )
                
                result.append(LayoutWord(
                    text=str(w.get('text', '')),
                    bbox=bbox,
                    confidence=float(w.get('confidence', 0)),
                    line_num=int(w.get('line_num', 0)),
                    word_num=int(w.get('word_num', 0)),
                    block_num=int(w.get('block_num', 0))
                ))
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"LayoutAnalyzer: Could not parse word: {e}")
                continue
        
        return result
    
    def _get_zone(self, y: int, header_end: int, footer_start: int) -> Zone:
        """Determine zone based on Y coordinate."""
        if y <= header_end:
            return Zone.HEADER
        elif y >= footer_start:
            return Zone.FOOTER
        else:
            return Zone.BODY
    
    def _group_into_lines(self) -> list[LayoutLine]:
        """Group words into lines based on Y position."""
        if not self.words:
            return []
        
        # Group by line_num from OCR
        line_groups: dict[int, list[LayoutWord]] = defaultdict(list)
        for word in self.words:
            line_groups[word.line_num].append(word)
        
        lines = []
        for line_num in sorted(line_groups.keys()):
            words = sorted(line_groups[line_num], key=lambda w: w.bbox.left)
            
            if not words:
                continue
            
            # Calculate line bounding box
            left = min(w.bbox.left for w in words)
            top = min(w.bbox.top for w in words)
            right = max(w.bbox.right for w in words)
            bottom = max(w.bbox.bottom for w in words)
            
            line_bbox = BoundingBox(
                left=left,
                top=top,
                width=right - left,
                height=bottom - top
            )
            
            # Calculate average word height
            avg_height = sum(w.bbox.height for w in words) / len(words)
            
            # Determine alignment
            alignment = self._detect_alignment(line_bbox)
            
            # Build text
            text = ' '.join(w.text for w in words)
            
            # Get zone from first word
            zone = words[0].zone if words else Zone.BODY
            
            lines.append(LayoutLine(
                words=words,
                bbox=line_bbox,
                line_num=line_num,
                zone=zone,
                alignment=alignment,
                text=text,
                average_word_height=avg_height
            ))
        
        return lines
    
    def _detect_alignment(self, bbox: BoundingBox) -> Alignment:
        """Detect text alignment based on position."""
        if self.page_width == 0:
            return Alignment.UNKNOWN
        
        left_margin = bbox.left
        right_margin = self.page_width - bbox.right
        
        # Check if centered
        if abs(left_margin - right_margin) < 50:
            return Alignment.CENTER
        
        # Check if right-aligned
        if right_margin < 50 and left_margin > 100:
            return Alignment.RIGHT
        
        return Alignment.LEFT
    
    def _detect_tables(self, lines: list[LayoutLine]) -> list[DetectedTable]:
        """Detect table structures based on column alignment."""
        tables = []
        
        # Look for groups of lines with aligned columns
        # This is a simplified heuristic - could be enhanced with ML
        
        # Find lines with multiple "columns" (large gaps between words)
        potential_table_lines = []
        
        for line in lines:
            if len(line.words) >= self.MIN_TABLE_COLUMNS:
                # Check for large gaps between words
                gaps = []
                for i in range(len(line.words) - 1):
                    gap = line.words[i + 1].bbox.left - line.words[i].bbox.right
                    gaps.append(gap)
                
                # If there are consistent gaps, might be a table row
                if gaps and max(gaps) > 30:
                    potential_table_lines.append(line)
        
        # Group consecutive table-like lines
        if len(potential_table_lines) >= self.MIN_TABLE_ROWS:
            # Check if they have aligned columns
            first_line = potential_table_lines[0]
            column_positions = [w.bbox.left for w in first_line.words]
            
            aligned_lines = [first_line]
            for line in potential_table_lines[1:]:
                # Check if column positions roughly match
                line_positions = [w.bbox.left for w in line.words]
                if self._columns_aligned(column_positions, line_positions):
                    aligned_lines.append(line)
            
            if len(aligned_lines) >= self.MIN_TABLE_ROWS:
                # Create table
                cells = []
                for row_idx, line in enumerate(aligned_lines):
                    for col_idx, word in enumerate(line.words):
                        cells.append(TableCell(
                            text=word.text,
                            row=row_idx,
                            col=col_idx,
                            bbox=word.bbox,
                            is_header=(row_idx == 0)
                        ))
                
                # Table bounding box
                all_bboxes = [line.bbox for line in aligned_lines]
                table_bbox = BoundingBox(
                    left=min(b.left for b in all_bboxes),
                    top=min(b.top for b in all_bboxes),
                    width=max(b.right for b in all_bboxes) - min(b.left for b in all_bboxes),
                    height=max(b.bottom for b in all_bboxes) - min(b.top for b in all_bboxes)
                )
                
                # Extract headers
                headers = [w.text for w in aligned_lines[0].words]
                
                tables.append(DetectedTable(
                    cells=cells,
                    rows=len(aligned_lines),
                    cols=len(column_positions),
                    bbox=table_bbox,
                    headers=headers
                ))
        
        return tables
    
    def _columns_aligned(
        self, 
        reference: list[int], 
        candidate: list[int]
    ) -> bool:
        """Check if column positions are roughly aligned."""
        if len(candidate) != len(reference):
            return False
        
        for ref, cand in zip(reference, candidate):
            if abs(ref - cand) > self.COLUMN_ALIGNMENT_TOLERANCE:
                return False
        
        return True
    
    def _empty_result(self) -> LayoutAnalysisResult:
        """Return empty result when no words to analyze."""
        return LayoutAnalysisResult(
            page_width=0,
            page_height=0,
            header_zone=(0, 0),
            body_zone=(0, 0),
            footer_zone=(0, 0),
            lines=[],
            tables=[],
            header_lines=[],
            footer_lines=[],
            prominent_lines=[],
            median_line_height=0,
            total_lines=0
        )
    
    # ==================== EXTRACTION HELPERS ====================
    
    def get_header_text(self, layout: LayoutAnalysisResult) -> str:
        """Get all text from header zone."""
        return '\n'.join(line.text for line in layout.header_lines)
    
    def get_footer_text(self, layout: LayoutAnalysisResult) -> str:
        """Get all text from footer zone."""
        return '\n'.join(line.text for line in layout.footer_lines)
    
    def get_prominent_text(self, layout: LayoutAnalysisResult) -> str:
        """Get all prominent (large) text."""
        return '\n'.join(line.text for line in layout.prominent_lines)
    
    def find_text_near_label(
        self,
        layout: LayoutAnalysisResult,
        label: str,
        search_direction: str = "right"  # "right", "below", "both"
    ) -> Optional[str]:
        """
        Find text near a label (for label-value extraction).
        
        Args:
            layout: Layout analysis result
            label: Label text to search for
            search_direction: Where to look for the value
            
        Returns:
            Text found near the label, or None
        """
        label_lower = label.lower()
        
        for line in layout.lines:
            for i, word in enumerate(line.words):
                if label_lower in word.text.lower():
                    # Found the label
                    
                    if search_direction in ["right", "both"]:
                        # Look for value to the right on same line
                        if i + 1 < len(line.words):
                            value_words = [w.text for w in line.words[i + 1:]]
                            if value_words:
                                return ' '.join(value_words)
                    
                    if search_direction in ["below", "both"]:
                        # Look for value on next line
                        line_idx = layout.lines.index(line)
                        if line_idx + 1 < len(layout.lines):
                            next_line = layout.lines[line_idx + 1]
                            if next_line.text.strip():
                                return next_line.text.strip()
        
        return None
    
    def find_amounts_in_zone(
        self,
        layout: LayoutAnalysisResult,
        zone: Zone
    ) -> list[tuple[float, LayoutLine]]:
        """
        Find all monetary amounts in a specific zone.
        
        Args:
            layout: Layout analysis result
            zone: Zone to search in
            
        Returns:
            List of (amount, line) tuples
        """
        zone_lines = [l for l in layout.lines if l.zone == zone]
        amounts = []
        
        for line in zone_lines:
            # Find numbers that look like amounts
            matches = re.findall(r'[\d,]+\.?\d*', line.text)
            for match in matches:
                try:
                    value = float(match.replace(',', ''))
                    if value > 0:
                        amounts.append((value, line))
                except ValueError:
                    continue
        
        return amounts
    
    def find_rightmost_amount(
        self,
        layout: LayoutAnalysisResult,
        zone: Zone = None
    ) -> Optional[tuple[float, LayoutLine]]:
        """
        Find the rightmost amount (often the total in receipts).
        
        Args:
            layout: Layout analysis result
            zone: Optional zone filter
            
        Returns:
            (amount, line) tuple or None
        """
        lines = layout.lines
        if zone:
            lines = [l for l in lines if l.zone == zone]
        
        rightmost = None
        rightmost_x = 0
        
        for line in lines:
            for word in line.words:
                # Check if word contains a number
                match = re.search(r'[\d,]+\.?\d*', word.text)
                if match:
                    try:
                        value = float(match.group().replace(',', ''))
                        if value > 0 and word.bbox.right > rightmost_x:
                            rightmost = (value, line)
                            rightmost_x = word.bbox.right
                    except ValueError:
                        continue
        
        return rightmost


def analyze_layout(
    text: str = None,
    ocr_words: list[dict] = None,
    page_width: int = 0,
    page_height: int = 0
) -> LayoutAnalysisResult:
    """
    Convenience function to analyze document layout.
    
    Args:
        text: Plain text (if ocr_words not available)
        ocr_words: Word-level OCR data with bounding boxes
        page_width: Page width
        page_height: Page height
        
    Returns:
        LayoutAnalysisResult
    """
    analyzer = LayoutAnalyzer()
    
    if ocr_words:
        return analyzer.analyze(ocr_words, page_width, page_height)
    elif text:
        return analyzer.analyze_from_text(text)
    else:
        return analyzer._empty_result()
