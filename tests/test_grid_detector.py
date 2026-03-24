"""Tests for grid detection engine."""
import pytest
from PIL import Image
from pixelmaker.core.extractor import extract_pixel_art
from pixelmaker.core.grid_detector import GridDetectionResult, detect_grid


class TestUniformGridDetection:
    """Feature 1.1: 균일 격자 감지"""

    def test_detects_correct_number_of_lines(self, uniform_grid_image):
        """1024x1024, 64x64 격자, 1px 검은선 → 63개 세로선 + 63개 가로선 감지"""
        img, grid_count, cell_size, colors = uniform_grid_image

        result = detect_grid(img)

        assert len(result.horizontal_lines) == 63
        assert len(result.vertical_lines) == 63

    def test_detection_confidence_above_threshold(self, uniform_grid_image):
        """신뢰도 > 0.9"""
        img, grid_count, cell_size, colors = uniform_grid_image

        result = detect_grid(img)

        assert result.confidence > 0.9

    def test_detected_grid_size(self, uniform_grid_image):
        """grid_size = 64 자동 결정"""
        img, grid_count, cell_size, colors = uniform_grid_image

        result = detect_grid(img)

        assert result.grid_size == 64


class TestNonuniformGridDetection:
    """Feature 1.2: 불균일 격자 감지"""

    def test_detects_all_cell_centers(self, nonuniform_grid_image):
        """검출된 셀 중심 수가 정확히 64x64"""
        img, grid_count, x_bounds, y_bounds, colors = nonuniform_grid_image

        result = detect_grid(img)

        # 63 lines means 64 cells
        assert len(result.horizontal_lines) == 63
        assert len(result.vertical_lines) == 63
        assert result.grid_size == 64

    def test_cell_centers_safe_margin_from_grid_lines(self, nonuniform_grid_image):
        """모든 셀 중심이 격자선에서 safe_margin(3px) 이상 떨어짐"""
        img, grid_count, x_bounds, y_bounds, colors = nonuniform_grid_image

        result = detect_grid(img)

        safe_margin = 3
        for i in range(len(result.horizontal_lines) - 1):
            gap = result.horizontal_lines[i + 1] - result.horizontal_lines[i]
            cell_center = result.horizontal_lines[i] + gap // 2
            assert cell_center - result.horizontal_lines[i] >= safe_margin
            assert result.horizontal_lines[i + 1] - cell_center >= safe_margin

        for i in range(len(result.vertical_lines) - 1):
            gap = result.vertical_lines[i + 1] - result.vertical_lines[i]
            cell_center = result.vertical_lines[i] + gap // 2
            assert cell_center - result.vertical_lines[i] >= safe_margin
            assert result.vertical_lines[i + 1] - cell_center >= safe_margin


class TestGrayGridLines:
    """Edge 3: 회색 격자선도 놓치지 않고 정상 추출"""

    def test_detects_gray_grid_lines(self, gray_line_grid_image):
        img, grid_count, colors = gray_line_grid_image
        result = detect_grid(img)
        assert result.grid_size == grid_count
        assert result.confidence > 0.5

    def test_extracts_correctly_with_gray_lines(self, gray_line_grid_image):
        img, grid_count, colors = gray_line_grid_image
        result = extract_pixel_art(img)
        assert result.size == (grid_count, grid_count)
        # Check first row colors match
        for col in range(min(5, grid_count)):
            got = result.getpixel((col, 0))[:3]
            expected = colors[col][:3] if len(colors[col]) > 3 else colors[col]
            assert got == expected, f"Pixel ({col},0): got {got}, expected {expected}"


class TestMixedThicknessGrid:
    """Edge 8: 불균일 격자선 두께"""

    def test_detects_mixed_thickness_grid(self, mixed_thickness_grid_image):
        """가장자리 2px + 내부 1px 혼합에서도 정상 감지"""
        img, grid_count, colors = mixed_thickness_grid_image
        result = detect_grid(img)
        assert result.grid_size == grid_count

    def test_extracts_with_mixed_thickness(self, mixed_thickness_grid_image):
        """셀 중심 정확히 샘플링"""
        img, grid_count, colors = mixed_thickness_grid_image
        result = extract_pixel_art(img)
        assert result.size == (grid_count, grid_count)


class TestNoGridDetection:
    """Feature 1.3a/1.3b: 격자 없는 입력"""

    def test_no_grid_no_hint_raises_error(self):
        """격자 없음 + 힌트 없음 → GridNotDetectedError"""
        from pixelmaker.core.errors import GridNotDetectedError
        # Plain colored image with no grid lines
        img = Image.new("RGB", (512, 512), (100, 150, 200))

        with pytest.raises(GridNotDetectedError):
            detect_grid(img)

    def test_no_grid_with_hint_fallback(self):
        """격자 없음 + --grid-size 32 → 32x32 fallback + warning"""
        img = Image.new("RGB", (512, 512), (100, 150, 200))
        result = detect_grid(img, grid_size=32)

        assert result.grid_size == 32
        # Should have 31 evenly spaced lines
        assert len(result.horizontal_lines) == 31
        assert len(result.vertical_lines) == 31
        # Low confidence indicates fallback
        assert result.confidence < 0.5


class TestHintConflict:
    """Feature 1.5: 힌트 충돌 검증"""

    def test_grid_size_ref_conflict_raises_error(self):
        """--grid-size 64 + ref=32x32.png → GridHintConflictError"""
        from pixelmaker.core.errors import GridHintConflictError
        img = Image.new("RGB", (512, 512), (100, 100, 100))
        ref = Image.new("RGB", (32, 32), (200, 200, 200))

        with pytest.raises(GridHintConflictError):
            detect_grid(img, grid_size=64, ref_image=ref)


class TestAutoDetectVsHintConflict:
    """Feature 1.6a/1.6b: 자동 감지 결과와 힌트 충돌"""

    def test_auto_detect_vs_grid_size_conflict(self, uniform_grid_image):
        """64x64 격자가 확실한 fixture + --grid-size 32 → GridHintConflictError"""
        from pixelmaker.core.errors import GridHintConflictError
        img, grid_count, cell_size, colors = uniform_grid_image

        with pytest.raises(GridHintConflictError):
            detect_grid(img, grid_size=32)

    def test_force_grid_size_overrides_auto_detect(self, uniform_grid_image):
        """64x64 격자가 확실한 fixture + --force-grid-size 32 → 32 적용, warning"""
        img, grid_count, cell_size, colors = uniform_grid_image

        result = detect_grid(img, force_grid_size=32)

        assert result.grid_size == 32
        assert len(result.horizontal_lines) == 31
        assert len(result.vertical_lines) == 31


class TestRefInference:
    """Feature 1.4: ref 파일로 격자 크기 추론"""

    def test_ref_image_infers_grid_size(self, uniform_grid_image):
        """ref=64x64.png → grid_size=64 자동 결정"""
        img, grid_count, cell_size, colors = uniform_grid_image
        ref = Image.new("RGB", (64, 64))

        result = detect_grid(img, ref_image=ref)

        assert result.grid_size == 64
