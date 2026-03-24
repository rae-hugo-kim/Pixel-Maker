from __future__ import annotations
from dataclasses import dataclass, field
from PIL import Image, ImageStat

from pixelmaker.core.errors import GridHintConflictError, GridNotDetectedError


@dataclass
class GridDetectionResult:
    horizontal_lines: list[int] = field(default_factory=list)
    vertical_lines: list[int] = field(default_factory=list)
    grid_size: int = 0
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)


def _row_mean(image: Image.Image, y: int) -> float:
    """Mean brightness of row y."""
    row = image.crop((0, y, image.width, y + 1))
    stat = ImageStat.Stat(row)
    return sum(stat.mean) / len(stat.mean)


def _col_mean(image: Image.Image, x: int) -> float:
    """Mean brightness of column x."""
    col = image.crop((x, 0, x + 1, image.height))
    stat = ImageStat.Stat(col)
    return sum(stat.mean) / len(stat.mean)


def _find_dark_positions(means: list[float], threshold: float = 10.0) -> list[int]:
    return [i for i, m in enumerate(means) if m < threshold]


def _find_valley_positions(means: list[float], window: int = 4, factor: float = 0.85) -> list[int]:
    """Find positions that are local valleys (significantly darker than neighbors).

    For each position i, compare its brightness to the median of a surrounding
    window. If it is significantly lower (< factor * neighbor_median), it is
    considered a grid line position.

    This detects gray grid lines that absolute-threshold detection misses.
    """
    n = len(means)
    result = []
    for i in range(n):
        lo = max(0, i - window)
        hi = min(n, i + window + 1)
        neighbors = [means[j] for j in range(lo, hi) if j != i]
        if not neighbors:
            continue
        sorted_n = sorted(neighbors)
        mid = len(sorted_n) // 2
        neighbor_median = (sorted_n[mid - 1] + sorted_n[mid]) / 2 if len(sorted_n) % 2 == 0 else sorted_n[mid]
        if means[i] < neighbor_median * factor:
            result.append(i)
    return result


def _cluster_midpoints(positions: list[int], gap: int = 2) -> list[int]:
    """Group consecutive positions into clusters, return midpoints."""
    if not positions:
        return []
    clusters: list[list[int]] = []
    current = [positions[0]]
    for pos in positions[1:]:
        if pos - current[-1] <= gap:
            current.append(pos)
        else:
            clusters.append(current)
            current = [pos]
    clusters.append(current)
    return [sum(c) // len(c) for c in clusters]


def _dominant_spacing(lines: list[int]) -> int:
    if len(lines) < 2:
        return 0
    diffs = [lines[i + 1] - lines[i] for i in range(len(lines) - 1)]
    counts: dict[int, int] = {}
    for d in diffs:
        counts[d] = counts.get(d, 0) + 1
    return max(counts, key=lambda k: counts[k])


def _filter_evenly_spaced(lines: list[int], tolerance: int = 3) -> list[int]:
    if len(lines) < 2:
        return lines
    spacing = _dominant_spacing(lines)
    if spacing == 0:
        return lines
    # Use average spacing from full span to avoid mode bias on jittered grids
    avg_spacing = (lines[-1] - lines[0]) / (len(lines) - 1)
    anchor = lines[0]
    result = []
    for line in lines:
        offset = line - anchor
        # Find nearest ideal position using average spacing
        n = round(offset / avg_spacing)
        ideal = anchor + n * avg_spacing
        if abs(line - ideal) <= tolerance:
            result.append(line)
    return result


def _confidence(lines: list[int]) -> float:
    if len(lines) < 2:
        return 0.0
    spacing = _dominant_spacing(lines)
    if spacing == 0:
        return 0.0
    matching = sum(
        1 for i in range(len(lines) - 1)
        if abs(lines[i + 1] - lines[i] - spacing) <= 2
    )
    return (matching + 1) / len(lines)


def _generate_evenly_spaced_lines(image_size: int, grid_size: int) -> list[int]:
    """Generate grid_size-1 evenly spaced internal line positions for a given image dimension."""
    n_lines = grid_size - 1
    step = image_size / grid_size
    return [round(step * (i + 1)) for i in range(n_lines)]


def detect_grid(
    image: Image.Image,
    grid_size: int | None = None,
    ref_image: Image.Image | None = None,
    force_grid_size: int | None = None,
) -> GridDetectionResult:
    # Feature 1.6b: force_grid_size bypasses auto-detection entirely
    if force_grid_size is not None:
        h_lines = _generate_evenly_spaced_lines(image.height, force_grid_size)
        v_lines = _generate_evenly_spaced_lines(image.width, force_grid_size)
        return GridDetectionResult(
            horizontal_lines=h_lines,
            vertical_lines=v_lines,
            grid_size=force_grid_size,
            confidence=0.1,  # forced override, low confidence
            warnings=[f"Warning: --force-grid-size override applied (grid_size={force_grid_size}); auto-detection skipped."],
        )

    # Feature 1.5: Hint conflict — grid_size and ref_image dimensions must agree
    if grid_size is not None and ref_image is not None:
        ref_w, ref_h = ref_image.size
        ref_grid = max(ref_w, ref_h)
        if ref_grid != grid_size:
            raise GridHintConflictError(
                f"grid_size={grid_size} conflicts with ref_image size {ref_image.size} "
                f"(implies grid_size={ref_grid})"
            )

    # Feature 1.4: infer grid_size from ref_image when no explicit grid_size given
    if ref_image is not None and grid_size is None:
        ref_w, ref_h = ref_image.size
        grid_size = max(ref_w, ref_h)

    width, height = image.size
    gray = image.convert("L")

    h_means = [_row_mean(gray, y) for y in range(height)]
    v_means = [_col_mean(gray, x) for x in range(width)]

    # Try absolute dark threshold first (fast path for black lines)
    h_dark = _find_dark_positions(h_means)
    v_dark = _find_dark_positions(v_means)

    h_lines = _cluster_midpoints(h_dark)
    v_lines = _cluster_midpoints(v_dark)

    # Remove border lines (lines within 2px of image edge are not internal grid lines)
    border_margin = 2
    h_lines = [y for y in h_lines if border_margin <= y <= height - 1 - border_margin]
    v_lines = [x for x in v_lines if border_margin <= x <= width - 1 - border_margin]

    h_lines = _filter_evenly_spaced(h_lines)
    v_lines = _filter_evenly_spaced(v_lines)

    # If absolute threshold found very few lines, try valley detection (handles gray lines)
    min_expected = 3  # need at least a few lines to trust the result
    if len(h_lines) < min_expected or len(v_lines) < min_expected:
        h_dark_v = _find_valley_positions(h_means)
        v_dark_v = _find_valley_positions(v_means)

        h_lines_v = _cluster_midpoints(h_dark_v)
        v_lines_v = _cluster_midpoints(v_dark_v)

        h_lines_v = [y for y in h_lines_v if border_margin <= y <= height - 1 - border_margin]
        v_lines_v = [x for x in v_lines_v if border_margin <= x <= width - 1 - border_margin]

        h_lines_v = _filter_evenly_spaced(h_lines_v)
        v_lines_v = _filter_evenly_spaced(v_lines_v)

        # Use valley results if they found more lines
        if len(h_lines_v) > len(h_lines):
            h_lines = h_lines_v
        if len(v_lines_v) > len(v_lines):
            v_lines = v_lines_v

    # Feature 1.3: No grid detected
    no_lines = len(h_lines) < min_expected and len(v_lines) < min_expected

    if no_lines:
        if grid_size is None:
            # Feature 1.3a: no hint → raise error
            raise GridNotDetectedError(
                "No grid lines detected and no grid_size hint provided."
            )
        else:
            # Feature 1.3b: fallback with hint — generate evenly spaced lines
            h_lines = _generate_evenly_spaced_lines(height, grid_size)
            v_lines = _generate_evenly_spaced_lines(width, grid_size)
            return GridDetectionResult(
                horizontal_lines=h_lines,
                vertical_lines=v_lines,
                grid_size=grid_size,
                confidence=0.1,  # low confidence = fallback
                warnings=[f"Warning: no grid detected; falling back to --grid-size={grid_size} hint."],
            )

    detected_grid_size = max(len(h_lines), len(v_lines)) + 1

    # Feature 1.6a: auto-detect result conflicts with grid_size hint → raise error
    if grid_size is not None and grid_size != detected_grid_size:
        raise GridHintConflictError(
            f"Auto-detected grid_size={detected_grid_size} conflicts with "
            f"provided grid_size={grid_size}"
        )

    h_conf = _confidence(h_lines)
    v_conf = _confidence(v_lines)
    confidence = (h_conf + v_conf) / 2 if (h_conf + v_conf) > 0 else 0.0

    return GridDetectionResult(
        horizontal_lines=h_lines,
        vertical_lines=v_lines,
        grid_size=detected_grid_size,
        confidence=confidence,
    )
