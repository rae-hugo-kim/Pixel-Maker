import random

import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def uniform_grid_image():
    """1024x1024 image with 64x64 grid cells separated by 1px black lines.

    Layout:
    - Black background acts as grid lines
    - Each cell is 15x15 pixels of random color
    - Cell (col, row) starts at x = col * 16, y = row * 16
    - Grid lines are the 1px black gaps at x = col*16 + 15, etc.
    - Total used area: 64 * 15 + 63 * 1 = 1023px; image is 1024px (extra black border at edge)
    """
    cell_size = 15
    grid_count = 64
    line_width = 1
    img_size = 1024

    random.seed(42)
    colors = [
        (random.randint(30, 225), random.randint(30, 225), random.randint(30, 225))
        for _ in range(grid_count * grid_count)
    ]

    # Black background = grid lines
    img = Image.new("RGB", (img_size, img_size), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    step = cell_size + line_width  # 16
    for row in range(grid_count):
        for col in range(grid_count):
            x = col * step
            y = row * step
            color = colors[row * grid_count + col]
            draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color)

    return img, grid_count, cell_size, colors


@pytest.fixture
def nonuniform_grid_image():
    """~1023x1023 image with 64x64 grid cells where grid line positions have ±1px jitter.

    Layout:
    - Black background acts as grid lines (1px)
    - Nominal cell size 15px, nominal spacing 16px (cell + line)
    - Each of the 63 internal grid lines shifts ±1px from its ideal position
    - random.seed(99) for reproducible jitter
    - Returns (img, grid_count, x_line_positions, y_line_positions, colors)
      where x_line_positions / y_line_positions are the 63 jittered grid line pixel coords.

    The ±1px positional jitter means consecutive line spacings vary by up to ±2px.
    This exceeds the tolerance window used by uniform-grid detection heuristics,
    causing the current _filter_evenly_spaced logic to discard most lines.
    Feature 1.2 must detect all 63 lines correctly despite the non-uniform spacing.
    """
    grid_count = 64
    nominal_spacing = 16  # 15px cell + 1px grid line

    rng = random.Random(99)

    # Ideal internal grid line positions (between cell i and cell i+1)
    ideal_x = [nominal_spacing * (i + 1) - 1 for i in range(grid_count - 1)]
    ideal_y = [nominal_spacing * (i + 1) - 1 for i in range(grid_count - 1)]

    # Apply ±1px positional jitter to each line
    x_lines = [p + rng.choice([-1, 0, 1]) for p in ideal_x]
    y_lines = [p + rng.choice([-1, 0, 1]) for p in ideal_y]

    # Image dimensions: last cell extends 15px beyond last grid line
    cell_tail = nominal_spacing - 1  # 15px
    img_width = x_lines[-1] + cell_tail + 1
    img_height = y_lines[-1] + cell_tail + 1

    colors = [
        (rng.randint(30, 225), rng.randint(30, 225), rng.randint(30, 225))
        for _ in range(grid_count * grid_count)
    ]

    # Black background = grid lines
    img = Image.new("RGB", (img_width, img_height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Build cell boundary lists from jittered line positions
    # Cell col starts at: 0 if col==0, else x_lines[col-1]+1
    # Cell col ends at:   x_lines[col]-1 if col<63, else img_width-1
    def _cell_starts(lines, img_size):
        starts = [0] + [p + 1 for p in lines]
        ends = [p - 1 for p in lines] + [img_size - 1]
        return starts, ends

    x_starts, x_ends = _cell_starts(x_lines, img_width)
    y_starts, y_ends = _cell_starts(y_lines, img_height)

    for row in range(grid_count):
        for col in range(grid_count):
            color = colors[row * grid_count + col]
            draw.rectangle(
                [x_starts[col], y_starts[row], x_ends[col], y_ends[row]],
                fill=color,
            )

    return img, grid_count, x_lines, y_lines, colors


@pytest.fixture
def transparent_grid_image():
    """RGBA image: transparent background + black grid lines + colored cells."""
    cell_size = 15
    grid_count = 32
    step = cell_size + 1
    img_size = grid_count * step

    random.seed(77)
    colors = [
        (random.randint(30, 225), random.randint(30, 225), random.randint(30, 225), 255)
        for _ in range(grid_count * grid_count)
    ]

    # Transparent background (alpha=0)
    img = Image.new("RGBA", (img_size, img_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw black grid lines (alpha=255) - draw full rows and columns
    for i in range(1, grid_count):
        line_pos = i * step - 1
        draw.line([(line_pos, 0), (line_pos, img_size - 1)], fill=(0, 0, 0, 255), width=1)
        draw.line([(0, line_pos), (img_size - 1, line_pos)], fill=(0, 0, 0, 255), width=1)

    # Fill cells with colors
    for row in range(grid_count):
        for col in range(grid_count):
            x = col * step
            y = row * step
            color = colors[row * grid_count + col]
            draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color)

    return img, grid_count, colors


@pytest.fixture
def jpeg_grid_image(uniform_grid_image, uniform_grid_ref_image, tmp_path):
    """Save uniform grid as JPEG quality=85, reload."""
    img, grid_count, cell_size, colors = uniform_grid_image
    ref = uniform_grid_ref_image

    jpeg_path = tmp_path / "grid.jpg"
    img.save(str(jpeg_path), "JPEG", quality=85)
    jpeg_img = Image.open(str(jpeg_path))
    jpeg_img.load()  # force load before tmp might be cleaned

    return jpeg_img, ref, tmp_path


@pytest.fixture
def grayscale_grid_image():
    """Grayscale (mode 'L') grid image, 32x32 grid."""
    cell_size = 15
    grid_count = 32
    step = cell_size + 1
    img_size = grid_count * step

    random.seed(55)
    values = [random.randint(50, 220) for _ in range(grid_count * grid_count)]

    img = Image.new("L", (img_size, img_size), 0)
    draw = ImageDraw.Draw(img)

    for row in range(grid_count):
        for col in range(grid_count):
            x = col * step
            y = row * step
            v = values[row * grid_count + col]
            draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=v)

    return img, grid_count, values


@pytest.fixture
def uniform_grid_ref_image(uniform_grid_image):
    """Expected 64x64 pixel art (ground truth) extracted from uniform_grid_image."""
    img, grid_count, cell_size, colors = uniform_grid_image
    ref = Image.new("RGB", (grid_count, grid_count))
    for row in range(grid_count):
        for col in range(grid_count):
            ref.putpixel((col, row), colors[row * grid_count + col])
    return ref


@pytest.fixture
def gray_line_grid_image():
    """32x32 grid image with GRAY (128,128,128) grid lines instead of black.

    Layout:
    - cell_size=15, step=16 (15px cell + 1px gray line)
    - Cells are colored with random bright colors (values > 160)
    - Gray lines separate cells; background is filled with gray
    - Image size: 512x512 (pad with gray if needed)
    """
    cell_size = 15
    grid_count = 32
    step = cell_size + 1  # 16
    line_color = (128, 128, 128)
    img_size = 512

    random.seed(7)
    colors = [
        (random.randint(160, 255), random.randint(160, 255), random.randint(160, 255))
        for _ in range(grid_count * grid_count)
    ]
    # Make sure no color accidentally matches gray lines
    colors = [
        (max(c[0], 165), max(c[1], 165), max(c[2], 165))
        for c in colors
    ]

    # Fill with gray (acts as grid lines everywhere outside cells)
    img = Image.new("RGB", (img_size, img_size), line_color)
    draw = ImageDraw.Draw(img)

    for row in range(grid_count):
        for col in range(grid_count):
            x = col * step
            y = row * step
            color = colors[row * grid_count + col]
            draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color)

    return img, grid_count, colors


@pytest.fixture
def mixed_thickness_grid_image():
    """16x16 grid with border (edge) lines 2px thick, internal lines 1px thick.

    Layout:
    - cell_size=20, internal line=1px, border line=2px
    - Each cell is 20x20 pixels of random color
    - Left/top border: 2px black; internal lines: 1px black; right/bottom border: 2px black
    """
    cell_size = 20
    grid_count = 16
    border_width = 2
    internal_width = 1

    random.seed(13)
    colors = [
        (random.randint(30, 225), random.randint(30, 225), random.randint(30, 225))
        for _ in range(grid_count * grid_count)
    ]

    # Compute image size: border(2) + grid_count*cell_size + (grid_count-1)*1 + border(2)
    # = 4 + 16*20 + 15 = 4 + 320 + 15 = 339
    img_width = border_width + grid_count * cell_size + (grid_count - 1) * internal_width + border_width
    img_height = img_width

    # Black background (acts as all lines)
    img = Image.new("RGB", (img_width, img_height), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fill each cell; cell (col,row) origin is:
    # x_start = border_width + col * (cell_size + internal_width)
    # y_start = border_width + row * (cell_size + internal_width)
    for row in range(grid_count):
        for col in range(grid_count):
            x = border_width + col * (cell_size + internal_width)
            y = border_width + row * (cell_size + internal_width)
            color = colors[row * grid_count + col]
            draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color)

    return img, grid_count, colors
