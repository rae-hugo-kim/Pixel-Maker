from __future__ import annotations
from PIL import Image, ImageStat


def _sample_cell(image: Image.Image, x0: int, x1: int, y0: int, y1: int) -> tuple:
    """Sample the representative color for a cell bounded by [x0,x1) x [y0,y1).

    For cells wide/tall enough to allow a 7x7 interior region, average that
    region to reduce JPEG compression artifacts. For smaller cells, fall back
    to single-pixel center sampling.
    """
    cell_w = x1 - x0
    cell_h = y1 - y0
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2

    # Use region averaging when cell is large enough (≥7px in both dimensions)
    region_half = 3  # 7x7 region
    if cell_w >= 7 and cell_h >= 7:
        rx0 = max(x0, cx - region_half)
        ry0 = max(y0, cy - region_half)
        rx1 = min(x1, cx + region_half + 1)
        ry1 = min(y1, cy + region_half + 1)
        region = image.crop((rx0, ry0, rx1, ry1))
        stat = ImageStat.Stat(region)
        return tuple(round(m) for m in stat.mean)

    return image.getpixel((cx, cy))


def extract_pixel_art(
    image: Image.Image,
    grid_size: int | None = None,
    ref_image: Image.Image | None = None,
    force_grid_size: int | None = None,
    scale: int | None = None,
) -> Image.Image:
    """Extract pixel art from grid-overlay image.

    Returns the extracted NxN pixel art image.
    """
    from pixelmaker.core.grid_detector import detect_grid

    detection = detect_grid(image, grid_size=grid_size, ref_image=ref_image, force_grid_size=force_grid_size)

    h_lines = detection.horizontal_lines
    v_lines = detection.vertical_lines

    # Build cell boundaries
    h_bounds = [0] + h_lines + [image.height]
    v_bounds = [0] + v_lines + [image.width]

    rows = len(h_bounds) - 1
    cols = len(v_bounds) - 1

    result = Image.new(image.mode, (cols, rows))

    for row in range(rows):
        y0 = h_bounds[row]
        y1 = h_bounds[row + 1]
        for col in range(cols):
            x0 = v_bounds[col]
            x1 = v_bounds[col + 1]
            pixel = _sample_cell(image, x0, x1, y0, y1)
            result.putpixel((col, row), pixel)

    # Optional scale
    if scale and scale > 1:
        result = result.resize((cols * scale, rows * scale), Image.NEAREST)

    return result
