"""Tests for CLI interface."""
import subprocess
import sys
import pytest
from PIL import Image


def run_cli(*args) -> subprocess.CompletedProcess:
    """Run pixelmaker CLI and return result."""
    return subprocess.run(
        [sys.executable, "-m", "pixelmaker.cli", *args],
        capture_output=True,
        text=True,
    )


class TestCLIBasicExecution:
    """Feature 3.1: 기본 실행"""

    def test_basic_extract(self, uniform_grid_image, tmp_path):
        """pixelmaker extract in.png out.png → 추출 성공, 파일 생성"""
        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img.save(str(in_path))

        result = run_cli("extract", str(in_path), str(out_path))

        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert out_path.exists()
        output_img = Image.open(str(out_path))
        assert output_img.size == (grid_count, grid_count)


class TestCLIOptions:
    """Feature 3.2: 옵션 지정"""

    def test_grid_size_and_scale_options(self, uniform_grid_image, tmp_path):
        """--grid-size 64 --scale 8 → 옵션 반영"""
        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img.save(str(in_path))

        result = run_cli("extract", str(in_path), str(out_path), "--grid-size", "64", "--scale", "8")

        assert result.returncode == 0, f"stderr: {result.stderr}"
        output_img = Image.open(str(out_path))
        assert output_img.size == (512, 512)


class TestCLIErrorHandling:
    """Feature 3.3/3.5: 에러 처리"""

    def test_invalid_path_error(self, tmp_path):
        """존재하지 않는 파일 → stderr에 에러, 종료코드 1"""
        result = run_cli("extract", "/nonexistent/file.png", str(tmp_path / "out.png"))
        assert result.returncode == 1
        assert result.stderr.strip() != ""

    def test_no_grid_no_hint_error(self, tmp_path):
        """격자 없는 이미지 + 힌트 없음 → stderr에 GridNotDetectedError, 종료코드 1"""
        plain_img = Image.new("RGB", (512, 512), (100, 150, 200))
        in_path = tmp_path / "plain.png"
        plain_img.save(str(in_path))

        result = run_cli("extract", str(in_path), str(tmp_path / "out.png"))
        assert result.returncode == 1
        assert "GridNotDetectedError" in result.stderr or "grid" in result.stderr.lower()


class TestCLIFallback:
    """Feature 3.6: 격자 미감지 + --grid-size → fallback + warning"""

    def test_fallback_with_grid_size(self, tmp_path):
        plain_img = Image.new("RGB", (512, 512), (100, 150, 200))
        in_path = tmp_path / "plain.png"
        out_path = tmp_path / "out.png"
        plain_img.save(str(in_path))

        result = run_cli("extract", str(in_path), str(out_path), "--grid-size", "32")

        assert result.returncode == 0
        assert "warning" in result.stderr.lower() or "fallback" in result.stderr.lower()
        assert out_path.exists()


class TestCLIHintConflict:
    """Feature 3.7/3.8: 힌트 충돌"""

    def test_grid_size_ref_conflict(self, uniform_grid_image, tmp_path):
        """--grid-size 64 --ref 32x32.png → stderr에 GridHintConflictError, 종료코드 1"""
        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        ref_path = tmp_path / "ref32.png"
        img.save(str(in_path))
        ref = Image.new("RGB", (32, 32))
        ref.save(str(ref_path))

        result = run_cli("extract", str(in_path), str(tmp_path / "out.png"),
                         "--grid-size", "64", "--ref", str(ref_path))
        assert result.returncode == 1
        assert "conflict" in result.stderr.lower() or "GridHintConflictError" in result.stderr

    def test_auto_detect_vs_grid_size_conflict(self, uniform_grid_image, tmp_path):
        """자동 감지 64 + --grid-size 32 → stderr에 에러, 종료코드 1"""
        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        img.save(str(in_path))

        result = run_cli("extract", str(in_path), str(tmp_path / "out.png"), "--grid-size", "32")
        assert result.returncode == 1


class TestCLIForceOverride:
    """Feature 3.9: --force-grid-size override"""

    def test_force_grid_size_override(self, uniform_grid_image, tmp_path):
        img, grid_count, cell_size, colors = uniform_grid_image
        in_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img.save(str(in_path))

        result = run_cli("extract", str(in_path), str(out_path), "--force-grid-size", "32")

        assert result.returncode == 0
        assert "warning" in result.stderr.lower() or "override" in result.stderr.lower()
        output_img = Image.open(str(out_path))
        assert output_img.size == (32, 32)
