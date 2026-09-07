"""Layout-aware formatter for PaddleOCR output.

Scanned government PDFs in Hindi often mix single-column paragraphs with
two-column tables. This module takes the raw PaddleOCR detection list and
rebuilds readable text by:

1. Clustering detections into columns using x-position.
2. Grouping detections in the same column into horizontal lines using y-position.
3. Sorting each line left-to-right and joining words with spaces.
4. Emitting columns in reading order (left to right, top to bottom).
"""

from __future__ import annotations

from typing import Any


def _center_y(bbox: list[list[float]]) -> float:
    """Average y-coordinate of a bounding-box quadrilateral."""
    return sum(p[1] for p in bbox) / len(bbox)


def _center_x(bbox: list[list[float]]) -> float:
    """Average x-coordinate of a bounding-box quadrilateral."""
    return sum(p[0] for p in bbox) / len(bbox)


def _height(bbox: list[list[float]]) -> float:
    ys = [p[1] for p in bbox]
    return max(ys) - min(ys)


def _width(bbox: list[list[float]]) -> float:
    xs = [p[0] for p in bbox]
    return max(xs) - min(xs)


def _detect_columns(detections: list[tuple[list[list[float]], str]], page_width: float) -> list[list[tuple[list[list[float]], str]]]:
    """Split detections into columns based on horizontal center positions.

    Uses a simple gap-based algorithm:
    - Sort detections by x-center.
    - Find the largest gaps between adjacent x-centers.
    - If a gap is > 25% of page width, treat it as a column boundary.
    """
    if not detections:
        return []

    # Single-column fallback threshold.
    min_gap_ratio = 0.20
    min_gap = page_width * min_gap_ratio

    sorted_by_x = sorted(detections, key=lambda d: _center_x(d[0]))

    # Find column split points by large horizontal gaps.
    splits: list[int] = [0]
    for i in range(1, len(sorted_by_x)):
        prev_x = _center_x(sorted_by_x[i - 1][0])
        curr_x = _center_x(sorted_by_x[i][0])
        if (curr_x - prev_x) > min_gap:
            splits.append(i)
    splits.append(len(sorted_by_x))

    columns: list[list[tuple[list[list[float]], str]]] = []
    for i in range(len(splits) - 1):
        columns.append(sorted_by_x[splits[i]:splits[i + 1]])

    return columns


def _lines_from_column(column: list[tuple[list[list[float]], str]]) -> list[str]:
    """Group detections in one column into lines sorted left-to-right."""
    if not column:
        return []

    # Sort by vertical center to walk down the column.
    column = sorted(column, key=lambda d: _center_y(d[0]))

    heights = [_height(d[0]) for d in column]
    median_height = sorted(heights)[len(heights) // 2] if heights else 12.0
    y_threshold = max(median_height * 0.65, 10.0)

    lines: list[list[tuple[float, str]]] = []
    current_line: list[tuple[float, str]] = []
    current_y: float | None = None

    for bbox, text in column:
        cy = _center_y(bbox)
        cx = _center_x(bbox)
        if current_y is None or abs(cy - current_y) <= y_threshold:
            current_line.append((cx, text.strip()))
            current_y = cy
        else:
            current_line.sort(key=lambda item: item[0])
            lines.append([t for _x, t in current_line])
            current_line = [(cx, text.strip())]
            current_y = cy

    if current_line:
        current_line.sort(key=lambda item: item[0])
        lines.append([t for _x, t in current_line])

    return [" ".join(line) for line in lines]


def format_ocr_page(detections: list[Any], page_width: float) -> str:
    """Format one page of PaddleOCR detections into readable text.

    Args:
        detections: PaddleOCR result[0] list for one page.
        page_width: Width of the rendered page image in pixels.

    Returns:
        Readable, line-structured text for the page.
    """
    if detections is None:
        return ""

    # Normalize to (bbox, text) tuples, skipping empty detections.
    items: list[tuple[list[list[float]], str]] = []
    for det in detections:
        if det is None:
            continue
        bbox, (text, _confidence) = det
        text = text.strip() if text else ""
        if text:
            items.append((bbox, text))

    if not items:
        return ""

    columns = _detect_columns(items, page_width)

    page_lines: list[str] = []
    for column in columns:
        lines = _lines_from_column(column)
        if lines:
            page_lines.extend(lines)

    return "\n".join(page_lines)
