## Kickoff Summary: PixelMaker — 격자 이미지에서 순수 픽셀아트 추출기

**Date**: 2026-03-24
**Type**: New Project

### JTBD
- User: 게임 개발자 (고화질 격자 이미지 생성 서비스 이용자)
- Problem: 격자선이 포함된 고해상도 이미지에서 순수 픽셀아트를 깨끗하게 추출할 방법이 없다
- Success: 격자 이미지를 넣으면 격자 없는 깨끗한 NxN 픽셀아트를 즉시 얻는 쉬운 워크플로우

### Context
- Repo type: 단일 저장소 (소스코드 신규 작성)
- Tech stack: Python + Pillow, MCP SDK (mcp[cli])
- Build/Test: pytest tests/
- Patterns: CLAUDE.md 정책 프레임워크, oh-my-claudecode 통합, harness 시스템

### Scope
- MUST:
  - 격자선 자동 감지 엔진
  - 셀 중심 색상 샘플링 → 순수 NxN 픽셀아트 추출
  - CLI 도구: `pixelmaker extract` (agent 친화적)
  - MCP 서버: `extract_pixel_art` 툴
  - Python + Pillow 기반
  - 힌트 충돌/부재 시 명확한 에러 (GridHintConflictError, GridNotDetectedError)
- SHOULD:
  - ref 이미지로 격자 크기 자동 추론
  - 추출 후 scale 옵션 (nearest neighbor 확대)
  - 배치 처리
- MUST NOT:
  - 임의 이미지를 픽셀아트 스타일로 변환하는 것 (다른 도구)
  - 원본 색상 임의 변경 (팔레트 양자화는 opt-in만)
- OUT OF SCOPE:
  - 실시간 프리뷰
  - 클라우드 배포
  - 애니메이션(GIF/스프라이트시트) 지원

### Acceptance Criteria
1. 균일 격자(1px 검은 선) 포함 고해상도 이미지에서 격자선을 자동 감지 (신뢰도 > 0.9)
2. 셀 중심 색상 샘플링으로 정확한 NxN 픽셀아트 추출
3. 무손실 입력 시 추출 색상 원본과 완전 일치 (불일치 = 0)
4. 손실 포맷(JPEG quality=85) 시 채널당 오차 ≤ 3, 불일치 < 5%
5. 출력 픽셀이 선명한 경계, 안티앨리어싱/블러 없음
6. 힌트 없음/있음/fallback/충돌 규칙 일관 동작
7. CLI `pixelmaker extract <input> <output> --options` 실행 가능
8. MCP `extract_pixel_art` 툴 + 메타데이터(confidence, grid_detected, fallback_used, grid_size, unique_colors, warnings)
9. PNG 투명 배경, JPG, BMP, WebP 등 다양한 포맷 지원
10. 그레이스케일 입력 정상 처리
11. 4K+ 초고해상도 CI 시간/메모리 예산 내 처리

### Edge Cases
- 투명 배경 + 검은 격자선 조합
- JPEG 압축 아티팩트
- 회색 격자선
- 셀 내부에 격자선보다 어두운 픽셀
- 불균일 격자 (±1px 흔들림)
- 불균일 격자선 두께 (가장자리 2px + 내부 1px)
- off-by-half 에러
- 1x1 입력 (힌트 유무에 따라 분기)
- 힌트 충돌 (--grid-size + --ref 불일치)

### Backpressure
- Method: 자동 테스트(pytest) + 샘플 이미지 육안 확인
- Command: `pytest tests/`

---
Kickoff complete. Ready for implementation.
Next: `/startdev` or manual planning.
