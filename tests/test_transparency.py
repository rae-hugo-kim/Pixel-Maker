"""Tests for transparent background feature."""
import random

import pytest
from PIL import Image, ImageDraw

from pixelmaker.core.extractor import extract_pixel_art, make_transparent


def _make_grid_image(grid_count, cell_size, bg_color, colors):
    """Helper: create grid image with given bg color and cell colors."""
    step = cell_size + 1
    img_size = grid_count * step
    img = Image.new("RGB", (img_size, img_size), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    for row in range(grid_count):
        for col in range(grid_count):
            x, y = col * step, row * step
            color = colors[row * grid_count + col]
            draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color)
    return img


class TestTransparentColor:
    """--transparent-color: 지정 색상을 edge-connected 투명화"""

    def test_specified_color_becomes_transparent(self):
        """배경색 (255,0,0) 지정 → 가장자리 연결된 빨간 픽셀만 투명"""
        # 4x4 pixel art: red border, blue center
        img = Image.new("RGB", (4, 4), (255, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([1, 1, 2, 2], fill=(0, 0, 255))

        result = make_transparent(img, color=(255, 0, 0))

        assert result.mode == "RGBA"
        # Edge red pixels should be transparent
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((3, 3))[3] == 0
        # Center blue pixels should be opaque
        assert result.getpixel((1, 1))[3] == 255
        assert result.getpixel((2, 2))[3] == 255

    def test_interior_same_color_stays_opaque(self):
        """가장자리와 연결되지 않은 동일 색상 내부 영역은 불투명 유지"""
        # 5x5: green border, blue ring, green center island
        img = Image.new("RGB", (5, 5), (0, 255, 0))
        draw = ImageDraw.Draw(img)
        # Blue ring at row/col 1-3
        for r in range(1, 4):
            for c in range(1, 4):
                draw.point((c, r), fill=(0, 0, 255))
        # Green island at center
        draw.point((2, 2), fill=(0, 255, 0))

        result = make_transparent(img, color=(0, 255, 0))

        # Edge green → transparent
        assert result.getpixel((0, 0))[3] == 0
        # Center green island → opaque (not edge-connected)
        assert result.getpixel((2, 2))[3] == 255

    def test_no_matching_edge_color_unchanged(self):
        """가장자리에 해당 색상이 없으면 변경 없음"""
        img = Image.new("RGB", (3, 3), (100, 100, 100))

        result = make_transparent(img, color=(255, 0, 0))

        assert result.mode == "RGBA"
        # All pixels should be opaque
        for y in range(3):
            for x in range(3):
                assert result.getpixel((x, y))[3] == 255


class TestTransparentBg:
    """--transparent-bg: 가장자리에서 자동 감지된 배경색을 edge-connected 투명화"""

    def test_auto_detects_edge_background(self):
        """가장자리 대다수 색상을 배경으로 자동 감지 → 투명화"""
        # 6x6: white border (20 edge pixels), red interior
        img = Image.new("RGB", (6, 6), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([1, 1, 4, 4], fill=(255, 0, 0))

        result = make_transparent(img, auto=True)

        assert result.mode == "RGBA"
        # Edge white → transparent
        assert result.getpixel((0, 0))[3] == 0
        assert result.getpixel((5, 5))[3] == 0
        # Interior red → opaque
        assert result.getpixel((2, 2))[3] == 255

    def test_auto_detect_no_dominant_edge_unchanged(self):
        """가장자리 색상이 다양하면 투명화하지 않음 (변경 없이 RGBA 반환)"""
        # 4x4 image with all different edge colors
        random.seed(999)
        img = Image.new("RGB", (4, 4))
        for y in range(4):
            for x in range(4):
                img.putpixel((x, y), (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

        result = make_transparent(img, auto=True)

        assert result.mode == "RGBA"
        # All should remain opaque (no dominant edge color)
        for y in range(4):
            for x in range(4):
                assert result.getpixel((x, y))[3] == 255


class TestTransparentIntegration:
    """extract_pixel_art + transparent 통합 테스트"""

    def test_extract_then_transparent_color(self, uniform_grid_image):
        """추출 후 transparent_color 적용"""
        img, grid_count, cell_size, colors = uniform_grid_image
        result = extract_pixel_art(img, transparent_color=(0, 0, 0))

        assert result.mode == "RGBA"
        assert result.size == (64, 64)

    def test_extract_then_transparent_bg(self):
        """배경이 흰색인 격자 → 추출 후 transparent_bg → 흰색 가장자리 투명"""
        cell_size = 15
        grid_count = 8
        step = cell_size + 1

        bg_white = (255, 255, 255)
        # All edge cells are white, center cells are colored
        colors = []
        for row in range(grid_count):
            for col in range(grid_count):
                if row == 0 or row == grid_count - 1 or col == 0 or col == grid_count - 1:
                    colors.append(bg_white)
                else:
                    colors.append((100, 50, 200))

        img = _make_grid_image(grid_count, cell_size, (0, 0, 0), colors)
        result = extract_pixel_art(img, transparent_bg=True)

        assert result.mode == "RGBA"
        # Corner pixel (edge-connected white) → transparent
        assert result.getpixel((0, 0))[3] == 0
        # Center pixel (purple) → opaque
        assert result.getpixel((4, 4))[3] == 255


class TestTransparentCLI:
    """CLI 옵션 테스트"""

    def test_transparent_color_cli(self, uniform_grid_image, tmp_path):
        """--transparent-color '#000000' → RGBA output"""
        from pixelmaker.cli import main
        import sys

        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img.save(str(in_path))

        sys.argv = ["pixelmaker", "extract", str(in_path), str(out_path),
                     "--transparent-color", "#000000"]
        main()

        output = Image.open(str(out_path))
        assert output.mode == "RGBA"

    def test_transparent_bg_cli(self, tmp_path):
        """--transparent-bg → RGBA output"""
        from pixelmaker.cli import main
        import sys

        # White-border image
        img = Image.new("RGB", (128, 128), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        grid_count = 8
        cell_size = 15
        step = cell_size + 1
        for row in range(grid_count):
            for col in range(grid_count):
                x, y = col * step, row * step
                if row == 0 or row == 7 or col == 0 or col == 7:
                    color = (255, 255, 255)
                else:
                    color = (100, 50, 200)
                draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color)

        in_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img.save(str(in_path))

        sys.argv = ["pixelmaker", "extract", str(in_path), str(out_path),
                     "--transparent-bg"]
        main()

        output = Image.open(str(out_path))
        assert output.mode == "RGBA"

    def test_both_options_error(self, tmp_path):
        """--transparent-color + --transparent-bg 동시 사용 → 에러"""
        from pixelmaker.cli import main
        import sys

        img = Image.new("RGB", (128, 128), (0, 0, 0))
        in_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img.save(str(in_path))

        sys.argv = ["pixelmaker", "extract", str(in_path), str(out_path),
                     "--transparent-color", "#000000", "--transparent-bg"]

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


class TestTransparentMCP:
    """MCP 서버 투명화 옵션 테스트"""

    def test_mcp_transparent_color(self, uniform_grid_image, tmp_path):
        """MCP transparent_color 파라미터"""
        from pixelmaker.mcp_server import extract_pixel_art_tool

        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img.save(str(in_path))

        result = extract_pixel_art_tool(
            str(in_path), str(out_path), transparent_color="#FF0000"
        )

        assert result.get("error") is not True
        output = Image.open(str(out_path))
        assert output.mode == "RGBA"

    def test_mcp_transparent_bg(self, uniform_grid_image, tmp_path):
        """MCP transparent_bg 파라미터"""
        from pixelmaker.mcp_server import extract_pixel_art_tool

        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img.save(str(in_path))

        result = extract_pixel_art_tool(
            str(in_path), str(out_path), transparent_bg=True
        )

        assert result.get("error") is not True
        output = Image.open(str(out_path))
        assert output.mode == "RGBA"
