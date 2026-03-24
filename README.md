# PixelMaker

Extract pure pixel art from grid-overlay images. Detects grid lines automatically, samples the center color of each cell, and outputs a clean NxN pixel art image.

**Not** a style converter — this tool extracts pixel art that already exists inside a high-resolution grid image.

## Install

```bash
pip install git+https://github.com/rae-hugo-kim/Pixel-Maker.git
```

Or clone and install locally:

```bash
git clone https://github.com/rae-hugo-kim/Pixel-Maker.git
cd Pixel-Maker
pip install .
```

## CLI Usage

```bash
# Basic — auto-detect grid
pixelmaker extract input.png output.png

# Provide grid size hint
pixelmaker extract input.png output.png --grid-size 64

# Infer grid size from a reference image
pixelmaker extract input.png output.png --ref reference_64x64.png

# Force grid size (skip auto-detection)
pixelmaker extract input.png output.png --force-grid-size 32

# Scale up the output (nearest-neighbor)
pixelmaker extract input.png output.png --scale 4
```

### Options

| Option | Description |
|--------|-------------|
| `--grid-size N` | Hint for expected grid size. Raises error if auto-detection disagrees. |
| `--ref PATH` | Reference image to infer grid size from its dimensions. |
| `--force-grid-size N` | Force grid size, bypassing auto-detection entirely. |
| `--scale N` | Scale up the output image by N using nearest-neighbor interpolation. |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (grid not detected, hint conflict, file not found, etc.) |

## MCP Server (for AI Agents)

Register PixelMaker as an MCP tool so Claude can call it from any project:

```bash
# Install with MCP dependencies
pip install "pixelmaker[mcp] @ git+https://github.com/rae-hugo-kim/Pixel-Maker.git"

# Register with Claude Code
claude mcp add --scope user pixelmaker -- python -m pixelmaker.mcp_server
```

Once registered, ask Claude:

> "Extract pixel art from this image" (provide the file path)

Claude will call the `extract_pixel_art` tool and return metadata including confidence, grid size, and unique color count.

## How It Works

1. **Grid Detection** — Scans rows/columns for dark lines (absolute threshold + relative valley detection for gray lines)
2. **Cell Sampling** — Computes cell boundaries from grid lines, samples 7x7 center average for JPEG tolerance
3. **Output** — Produces a clean NxN pixel art image with exact original colors

## Supported Formats

| Format | Input | Output |
|--------|-------|--------|
| PNG | Yes | Yes |
| JPEG | Yes | — |
| BMP | Yes | — |
| WebP | Yes | — |
| RGBA (transparent) | Yes | — |
| Grayscale | Yes | — |

## Requirements

- Python 3.10+
- Pillow 10.0+

## Development

```bash
git clone https://github.com/rae-hugo-kim/Pixel-Maker.git
cd Pixel-Maker
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcp]"
python -m pytest  # 50 tests
```

## License

See repository for license details.

---

# PixelMaker (한국어)

격자선이 포함된 고해상도 이미지에서 순수 픽셀아트를 추출하는 도구입니다. 격자를 자동 감지하고, 각 셀의 중심 색상을 샘플링하여 깨끗한 NxN 픽셀아트 이미지를 출력합니다.

스타일 변환 도구가 **아닙니다** — 고해상도 격자 이미지 안에 이미 존재하는 픽셀아트를 꺼내는 도구입니다.

## 설치

```bash
pip install git+https://github.com/rae-hugo-kim/Pixel-Maker.git
```

또는 클론 후 로컬 설치:

```bash
git clone https://github.com/rae-hugo-kim/Pixel-Maker.git
cd Pixel-Maker
pip install .
```

## CLI 사용법

```bash
# 기본 — 격자 자동 감지
pixelmaker extract input.png output.png

# 격자 크기 힌트 제공
pixelmaker extract input.png output.png --grid-size 64

# 레퍼런스 이미지로 격자 크기 추론
pixelmaker extract input.png output.png --ref reference_64x64.png

# 격자 크기 강제 지정 (자동 감지 무시)
pixelmaker extract input.png output.png --force-grid-size 32

# 출력 이미지 확대 (nearest-neighbor)
pixelmaker extract input.png output.png --scale 4
```

### 옵션

| 옵션 | 설명 |
|------|------|
| `--grid-size N` | 예상 격자 크기 힌트. 자동 감지 결과와 다르면 에러 발생. |
| `--ref 경로` | 레퍼런스 이미지의 크기로 격자 크기를 추론. |
| `--force-grid-size N` | 자동 감지를 무시하고 격자 크기를 강제 지정. |
| `--scale N` | 출력 이미지를 N배 확대 (nearest-neighbor 보간). |

### 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 에러 (격자 미감지, 힌트 충돌, 파일 미발견 등) |

## MCP 서버 (AI 에이전트용)

PixelMaker를 MCP 도구로 등록하면 Claude가 어떤 프로젝트에서든 호출할 수 있습니다:

```bash
# MCP 의존성 포함 설치
pip install "pixelmaker[mcp] @ git+https://github.com/rae-hugo-kim/Pixel-Maker.git"

# Claude Code에 등록
claude mcp add --scope user pixelmaker -- python -m pixelmaker.mcp_server
```

등록 후 Claude에게 이렇게 말하면 됩니다:

> "이 이미지에서 픽셀아트 추출해줘" (파일 경로 제공)

Claude가 `extract_pixel_art` 도구를 호출하고, 신뢰도/격자 크기/고유 색상 수 등의 메타데이터를 반환합니다.

## 동작 원리

1. **격자 감지** — 각 행/열의 밝기를 스캔하여 격자선 위치를 찾음 (절대 임계값 + 회색 선용 상대 valley 감지)
2. **셀 샘플링** — 격자선에서 셀 경계를 계산하고, 중심 7x7 영역의 평균 색상을 샘플링 (JPEG 아티팩트 보정)
3. **출력** — 원본 색상이 보존된 깨끗한 NxN 픽셀아트 이미지 생성

## 지원 포맷

| 포맷 | 입력 | 출력 |
|------|------|------|
| PNG | O | O |
| JPEG | O | — |
| BMP | O | — |
| WebP | O | — |
| RGBA (투명 배경) | O | — |
| 그레이스케일 | O | — |

## 요구사항

- Python 3.10+
- Pillow 10.0+

## 개발 환경

```bash
git clone https://github.com/rae-hugo-kim/Pixel-Maker.git
cd Pixel-Maker
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,mcp]"
python -m pytest  # 50개 테스트
```

## 라이선스

저장소의 라이선스 파일을 참고하세요.
