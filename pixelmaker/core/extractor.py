from __future__ import annotations
from collections import Counter
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


def make_transparent(
    image: Image.Image,
    color: tuple | None = None,
    auto: bool = False,
) -> Image.Image:
    """Make edge-connected background pixels transparent.

    Args:
        image: Input image (RGB or RGBA).
        color: Specific RGB color to treat as background.
        auto: Auto-detect background from edge pixel majority.

    Returns RGBA image with edge-connected background pixels set to alpha=0.
    """
    rgb = image.convert("RGB")
    w, h = rgb.size

    if auto and color is None:
        # Collect edge pixels
        edge_pixels = []
        for x in range(w):
            edge_pixels.append(rgb.getpixel((x, 0)))
            edge_pixels.append(rgb.getpixel((x, h - 1)))
        for y in range(1, h - 1):
            edge_pixels.append(rgb.getpixel((0, y)))
            edge_pixels.append(rgb.getpixel((w - 1, y)))

        if not edge_pixels:
            return image.convert("RGBA")

        counts = Counter(edge_pixels)
        most_common_color, most_common_count = counts.most_common(1)[0]
        # Need >50% of edge pixels to be the same color
        if most_common_count <= len(edge_pixels) * 0.5:
            return image.convert("RGBA")
        color = most_common_color

    if color is None:
        return image.convert("RGBA")

    # Flood fill from all edge pixels matching `color`
    rgba = image.convert("RGBA")
    pixels = rgb.load()
    visited = [[False] * h for _ in range(w)]
    queue = []

    # Seed from all 4 edges
    for x in range(w):
        for y in [0, h - 1]:
            if pixels[x, y] == color and not visited[x][y]:
                visited[x][y] = True
                queue.append((x, y))
    for y in range(1, h - 1):
        for x in [0, w - 1]:
            if pixels[x, y] == color and not visited[x][y]:
                visited[x][y] = True
                queue.append((x, y))

    # BFS flood fill
    i = 0
    while i < len(queue):
        cx, cy = queue[i]
        i += 1
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny]:
                if pixels[nx, ny] == color:
                    visited[nx][ny] = True
                    queue.append((nx, ny))

    # Set transparent
    for x, y in queue:
        r, g, b = pixels[x, y]
        rgba.putpixel((x, y), (r, g, b, 0))

    return rgba


def extract_pixel_art(
    image: Image.Image,
    grid_size: int | None = None,
    ref_image: Image.Image | None = None,
    force_grid_size: int | None = None,
    scale: int | None = None,
    transparent_color: tuple | None = None,
    transparent_bg: bool = False,
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

    # Optional transparency
    if transparent_color is not None:
        result = make_transparent(result, color=transparent_color)
    elif transparent_bg:
        result = make_transparent(result, auto=True)

    return result
