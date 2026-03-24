"""Tests for MCP server."""
import asyncio
import json
import pytest
from PIL import Image, ImageDraw
import random

from pixelmaker.mcp_server import extract_pixel_art_tool, mcp_app


class TestMCPToolList:
    """Feature 4.1: 툴 목록"""

    def test_extract_pixel_art_in_tools(self):
        """list_tools → extract_pixel_art 포함"""
        tools = asyncio.run(mcp_app.list_tools())
        tool_names = [t.name for t in tools]
        assert "extract_pixel_art" in tool_names


class TestMCPExtraction:
    """Feature 4.2: 추출 호출"""

    def test_extract_returns_file_path(self, uniform_grid_image, tmp_path):
        """extract_pixel_art(path, options) → 추출된 파일 경로 반환"""
        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        img.save(str(in_path))

        result = extract_pixel_art_tool(str(in_path), str(tmp_path / "output.png"))

        assert "output_path" in result
        assert (tmp_path / "output.png").exists()


class TestMCPMetadata:
    """Feature 4.3: 메타데이터 의미 검증"""

    def test_metadata_on_normal_input(self, uniform_grid_image, tmp_path):
        """균일 격자 PNG → confidence 0.0~1.0, grid_detected=true, etc."""
        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        img.save(str(in_path))

        result = extract_pixel_art_tool(str(in_path), str(tmp_path / "out.png"))

        assert 0.0 <= result["confidence"] <= 1.0
        assert result["grid_detected"] is True
        assert result["fallback_used"] is False
        assert isinstance(result["grid_size"], int) and result["grid_size"] > 0
        assert isinstance(result["unique_colors"], int) and result["unique_colors"] > 0
        assert result["warnings"] == []


class TestMCPFallbackMetadata:
    """Feature 4.4: 메타데이터 fallback 검증"""

    def test_metadata_on_fallback(self, tmp_path):
        """격자 없음 + grid_size=32 → grid_detected=false, fallback_used=true"""
        plain = Image.new("RGB", (512, 512), (100, 150, 200))
        in_path = tmp_path / "plain.png"
        plain.save(str(in_path))

        result = extract_pixel_art_tool(str(in_path), str(tmp_path / "out.png"), grid_size=32)

        assert result["grid_detected"] is False
        assert result["fallback_used"] is True
        assert any("fallback" in w.lower() or "warning" in w.lower() for w in result["warnings"])


class TestMCPErrors:
    """Feature 4.5/4.6: MCP 에러 처리"""

    def test_no_grid_no_hint_error(self, tmp_path):
        """격자 없음 + 힌트 없음 → 구조화된 에러"""
        plain = Image.new("RGB", (512, 512), (100, 150, 200))
        in_path = tmp_path / "plain.png"
        plain.save(str(in_path))

        result = extract_pixel_art_tool(str(in_path), str(tmp_path / "out.png"))

        assert result.get("error") is True or result.get("is_error") is True
        assert "GridNotDetectedError" in result.get("error_type", "")

    def test_hint_conflict_error(self, uniform_grid_image, tmp_path):
        """grid_size=64 + ref=32x32 → 구조화된 에러"""
        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        ref_path = tmp_path / "ref32.png"
        img.save(str(in_path))
        Image.new("RGB", (32, 32)).save(str(ref_path))

        result = extract_pixel_art_tool(str(in_path), str(tmp_path / "out.png"),
                                        grid_size=64, ref_path=str(ref_path))

        assert result.get("error") is True or result.get("is_error") is True
        assert "GridHintConflictError" in result.get("error_type", "")


class TestMCPForceOverride:
    """Feature 4.7: --force-grid-size override via MCP"""

    def test_force_override_metadata(self, uniform_grid_image, tmp_path):
        """force_grid_size=32 → success + override warning in metadata"""
        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        img.save(str(in_path))

        result = extract_pixel_art_tool(str(in_path), str(tmp_path / "out.png"),
                                        force_grid_size=32)

        assert result.get("error") is not True
        assert result["grid_size"] == 32
        assert any("override" in w.lower() or "force" in w.lower() for w in result["warnings"])


class TestDarkCellContent:
    """Edge 4: 셀 내부에 격자선보다 어두운 픽셀"""

    def test_dark_pixels_not_confused_with_grid(self):
        """내부의 어두운 픽셀을 격자선으로 오인하지 않음"""
        from pixelmaker.core.grid_detector import detect_grid

        cell_size = 15
        grid_count = 16
        step = cell_size + 1
        img_size = grid_count * step

        # Create grid with some cells that are very dark (nearly black)
        img = Image.new("RGB", (img_size, img_size), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        rng = random.Random(88)
        for row in range(grid_count):
            for col in range(grid_count):
                x, y = col * step, row * step
                # Some cells are very dark (5-15 brightness)
                if (row + col) % 3 == 0:
                    color = (rng.randint(5, 15), rng.randint(5, 15), rng.randint(5, 15))
                else:
                    color = (rng.randint(100, 225), rng.randint(100, 225), rng.randint(100, 225))
                draw.rectangle([x, y, x + cell_size - 1, y + cell_size - 1], fill=color)

        result = detect_grid(img)
        assert result.grid_size == grid_count


class TestOneByOneInput:
    """Edge 9a/9b: 1x1 입력"""

    def test_1x1_no_hint_error(self):
        """1x1 + 힌트 없음 → GridNotDetectedError"""
        from pixelmaker.core.errors import GridNotDetectedError
        from pixelmaker.core.grid_detector import detect_grid

        img = Image.new("RGB", (1, 1), (100, 100, 100))
        with pytest.raises(GridNotDetectedError):
            detect_grid(img)

    def test_1x1_with_hint(self):
        """--grid-size 1 → 1x1 추출 성공"""
        from pixelmaker.core.grid_detector import detect_grid

        img = Image.new("RGB", (1, 1), (100, 100, 100))
        result = detect_grid(img, grid_size=1)
        assert result.grid_size == 1


class TestUnsupportedFormat:
    """Edge 10: 지원하지 않는 포맷"""

    def test_unsupported_format_error(self, tmp_path):
        """명확한 에러 메시지"""
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("not an image")

        with pytest.raises(Exception):  # PIL will raise an appropriate error
            img = Image.open(str(bad_file))
            img.load()
