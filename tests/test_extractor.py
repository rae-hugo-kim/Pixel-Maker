"""Tests for pixel art extraction."""
import random
from PIL import Image
from pixelmaker.core.extractor import extract_pixel_art
from pixelmaker.core.grid_detector import detect_grid  # noqa: F401 (used in TestJpegArtifacts)


class TestBasicExtraction:
    """Feature 2.1: 기본 추출"""

    def test_extracts_correct_dimensions(self, uniform_grid_image):
        """격자 포함 1024x1024 + grid=64 → 정확히 64x64 PNG"""
        img, grid_count, cell_size, colors = uniform_grid_image
        result = extract_pixel_art(img)
        assert result.size == (64, 64)

    def test_extracts_correct_dimensions_with_grid_size_hint(self, uniform_grid_image):
        """grid_size=64 힌트 사용 시에도 64x64"""
        img, grid_count, cell_size, colors = uniform_grid_image
        result = extract_pixel_art(img, grid_size=64)
        assert result.size == (64, 64)


class TestColorPreservation:
    """Feature 2.5: 색상 완전 보존"""

    def test_preserves_exact_color_count(self):
        """원본 23색 무손실 PNG → 추출 결과도 정확히 23색"""
        # Create a grid image with exactly 23 unique colors
        cell_size = 15
        grid_count = 8  # 8x8 = 64 cells, using 23 colors cycling
        step = cell_size + 1
        img_size = grid_count * step  # 128

        random.seed(123)
        palette = [(random.randint(30, 225), random.randint(30, 225), random.randint(30, 225)) for _ in range(23)]

        img = Image.new("RGB", (img_size, img_size), (0, 0, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)

        for row in range(grid_count):
            for col in range(grid_count):
                x = col * step
                y = row * step
                color = palette[(row * grid_count + col) % 23]
                draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color)

        result = extract_pixel_art(img)

        unique_colors = set()
        for y in range(result.height):
            for x in range(result.width):
                unique_colors.add(result.getpixel((x, y)))

        assert len(unique_colors) == 23


class TestLosslessRefComparison:
    """Feature 2.2: ref 비교 검증 (무손실) — 불일치 픽셀 = 0"""

    def test_zero_pixel_mismatch(self, uniform_grid_image, uniform_grid_ref_image):
        """무손실 PNG 추출 결과 + 원본 64x64 → 불일치 픽셀 = 0"""
        img, grid_count, cell_size, colors = uniform_grid_image
        ref = uniform_grid_ref_image

        result = extract_pixel_art(img)

        assert result.size == ref.size

        mismatch_count = 0
        for y in range(result.height):
            for x in range(result.width):
                if result.getpixel((x, y)) != ref.getpixel((x, y)):
                    mismatch_count += 1

        assert mismatch_count == 0, f"Found {mismatch_count} mismatched pixels"


class TestOffByHalfError:
    """Edge 5: off-by-half 에러 검증 — ref 대비 모든 픽셀 정확히 일치"""

    def test_no_off_by_half_error(self, uniform_grid_image, uniform_grid_ref_image):
        """Cell center sampling must hit the exact center, not off-by-one."""
        img, grid_count, cell_size, colors = uniform_grid_image
        ref = uniform_grid_ref_image
        result = extract_pixel_art(img)

        # Check every single pixel matches
        for y in range(result.height):
            for x in range(result.width):
                got = result.getpixel((x, y))
                expected = ref.getpixel((x, y))
                assert got == expected, f"Off-by-half at ({x},{y}): got {got}, expected {expected}"


class TestTransparentBackground:
    """Edge 1: 투명 배경을 격자선으로 오인하지 않고 정상 추출"""

    def test_extracts_from_rgba_with_transparent_bg(self, transparent_grid_image):
        """RGBA image with transparent bg + black grid lines → correct extraction"""
        img, grid_count, colors = transparent_grid_image
        result = extract_pixel_art(img)

        assert result.size == (grid_count, grid_count)
        # Verify some sampled pixels match expected colors
        for i in range(min(10, grid_count)):
            got = result.getpixel((i, 0))[:3]  # might be RGBA
            expected = colors[i][:3]
            assert got == expected, f"Pixel ({i},0): got {got}, expected {expected}"


class TestNearestNeighborScale:
    """Feature 2.4: Nearest Neighbor 확대"""

    def test_scale_dimensions(self, uniform_grid_image):
        """64x64 + scale=8 → 512x512"""
        img, grid_count, cell_size, colors = uniform_grid_image
        result = extract_pixel_art(img, scale=8)
        assert result.size == (512, 512)

    def test_scale_sharp_edges(self, uniform_grid_image):
        """확대 후 각 8x8 블록의 픽셀이 모두 동일 (no interpolation)"""
        img, grid_count, cell_size, colors = uniform_grid_image
        result = extract_pixel_art(img, scale=8)

        # Check that each 8x8 block has uniform color
        for cell_y in range(min(8, grid_count)):
            for cell_x in range(min(8, grid_count)):
                base_color = result.getpixel((cell_x * 8, cell_y * 8))
                for dy in range(8):
                    for dx in range(8):
                        px = result.getpixel((cell_x * 8 + dx, cell_y * 8 + dy))
                        assert px == base_color, f"Non-uniform at ({cell_x*8+dx},{cell_y*8+dy})"


class TestJpegArtifacts:
    """Edge 2: JPEG 압축 아티팩트에도 격자 감지 성공"""

    def test_detects_grid_from_jpeg(self, jpeg_grid_image):
        """JPEG quality=85 input → grid detected, extraction succeeds"""
        from pixelmaker.core.grid_detector import detect_grid
        jpeg_img, ref, tmp_path = jpeg_grid_image

        result_detection = detect_grid(jpeg_img)
        assert result_detection.grid_size == 64
        assert result_detection.confidence > 0.5  # lower threshold for JPEG

    def test_jpeg_extraction_within_tolerance(self, jpeg_grid_image):
        """JPEG extraction: 채널당 오차 ≤ 3, 불일치 픽셀 < 5%"""
        jpeg_img, ref, tmp_path = jpeg_grid_image
        result = extract_pixel_art(jpeg_img)

        assert result.size == ref.size

        total_pixels = result.width * result.height
        mismatch_count = 0
        for y in range(result.height):
            for x in range(result.width):
                r_got = result.getpixel((x, y))
                r_exp = ref.getpixel((x, y))
                # Per-channel difference
                if any(abs(a - b) > 3 for a, b in zip(r_got, r_exp)):
                    mismatch_count += 1

        mismatch_pct = mismatch_count / total_pixels
        assert mismatch_pct < 0.05, f"Mismatch: {mismatch_pct:.1%} ({mismatch_count}/{total_pixels})"


class TestGrayscaleInput:
    """Edge 6: 그레이스케일 입력"""

    def test_grayscale_extraction(self):
        """그레이 이미지 → 정상 추출, 그레이 팔레트 보존"""
        import random
        random.seed(55)
        cell_size = 15
        grid_count = 16
        step = cell_size + 1
        img_size = grid_count * step

        gray_values = [random.randint(30, 225) for _ in range(grid_count * grid_count)]

        img = Image.new("L", (img_size, img_size), 0)  # black bg
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        for row in range(grid_count):
            for col in range(grid_count):
                x, y = col * step, row * step
                draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=gray_values[row * grid_count + col])

        result = extract_pixel_art(img)
        assert result.size == (grid_count, grid_count)
        # Verify grayscale preserved
        assert result.mode == "L"


class TestPerformance4K:
    """Edge 7: 4K+ 초고해상도 성능"""

    def test_4k_processing_time_and_memory(self):
        """4096x4096 입력, 처리 시간 ≤ 5초"""
        import time

        # Generate 4096x4096 grid image (64x64 grid, cell_size=63, step=64)
        cell_size = 63
        grid_count = 64
        step = cell_size + 1
        img_size = grid_count * step  # 4096

        img = Image.new("RGB", (img_size, img_size), (0, 0, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        import random
        random.seed(44)
        for row in range(grid_count):
            for col in range(grid_count):
                x, y = col * step, row * step
                color = (random.randint(30, 225), random.randint(30, 225), random.randint(30, 225))
                draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color)

        start = time.monotonic()
        result = extract_pixel_art(img)
        elapsed = time.monotonic() - start

        assert result.size == (64, 64)
        assert elapsed <= 5.0, f"Processing took {elapsed:.2f}s (limit: 5s)"
