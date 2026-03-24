"""Tests for input format support."""
import pytest
from PIL import Image
from pixelmaker.core.extractor import extract_pixel_art
from pixelmaker.core.grid_detector import detect_grid


class TestPNGInput:
    """Feature 5.1: PNG 입력"""

    def test_png_extraction(self, uniform_grid_image, uniform_grid_ref_image, tmp_path):
        img, grid_count, cell_size, colors = uniform_grid_image
        png_path = tmp_path / "test.png"
        img.save(str(png_path), "PNG")
        loaded = Image.open(str(png_path))
        loaded.load()

        result = extract_pixel_art(loaded)
        ref = uniform_grid_ref_image
        assert result.size == ref.size


class TestJPEGInput:
    """Feature 5.2: JPEG 입력"""

    def test_jpeg_extraction_with_warning(self, uniform_grid_image, tmp_path):
        img, grid_count, cell_size, colors = uniform_grid_image
        jpg_path = tmp_path / "test.jpg"
        img.save(str(jpg_path), "JPEG", quality=85)
        loaded = Image.open(str(jpg_path))
        loaded.load()

        result = extract_pixel_art(loaded)
        assert result.size == (grid_count, grid_count)


class TestWebPInput:
    """Feature 5.3: WebP 입력 (lossless)"""

    def test_webp_lossless_extraction(self, uniform_grid_image, uniform_grid_ref_image, tmp_path):
        img, grid_count, cell_size, colors = uniform_grid_image
        webp_path = tmp_path / "test.webp"
        img.save(str(webp_path), "WEBP", lossless=True)
        loaded = Image.open(str(webp_path))
        loaded.load()

        result = extract_pixel_art(loaded)
        ref = uniform_grid_ref_image
        assert result.size == ref.size

        # Lossless → 0 mismatch
        mismatch = 0
        for y in range(result.height):
            for x in range(result.width):
                if result.getpixel((x, y)) != ref.getpixel((x, y)):
                    mismatch += 1
        assert mismatch == 0


class TestBMPInput:
    """Feature 5.4: BMP 입력"""

    def test_bmp_extraction(self, uniform_grid_image, tmp_path):
        img, grid_count, cell_size, colors = uniform_grid_image
        bmp_path = tmp_path / "test.bmp"
        img.save(str(bmp_path), "BMP")
        loaded = Image.open(str(bmp_path))
        loaded.load()

        result = extract_pixel_art(loaded)
        assert result.size == (grid_count, grid_count)
