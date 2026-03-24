# Current Scope: PixelMaker — 격자 이미지에서 순수 픽셀아트 추출기

**Created**: 2026-03-24

## MUST
- 격자선 자동 감지 엔진
- 셀 중심 색상 샘플링 → 순수 NxN 픽셀아트 추출
- CLI 도구: `pixelmaker extract` (agent 친화적)
- MCP 서버: `extract_pixel_art` 툴
- Python + Pillow 기반
- 힌트 충돌/부재 시 명확한 에러 (GridHintConflictError, GridNotDetectedError)

## SHOULD
- ref 이미지로 격자 크기 자동 추론
- 추출 후 scale 옵션 (nearest neighbor 확대)
- 배치 처리

## MUST NOT
- 임의 이미지를 픽셀아트 스타일로 변환하는 것 (다른 도구)
- 원본 색상 임의 변경 (팔레트 양자화는 opt-in만)

## OUT OF SCOPE
- 실시간 프리뷰
- 클라우드 배포
- 애니메이션(GIF/스프라이트시트) 지원

## Acceptance Criteria
- [x] 균일 격자(1px 검은 선) 포함 고해상도 이미지에서 격자선 자동 감지 (신뢰도 > 0.9)
- [x] 셀 중심 색상 샘플링으로 정확한 NxN 픽셀아트 추출
- [x] 무손실 입력 시 추출 색상 원본과 완전 일치 (불일치 = 0)
- [x] 손실 포맷(JPEG quality=85) 시 채널당 오차 ≤ 3, 불일치 < 5%
- [x] 출력 픽셀이 선명한 경계, 안티앨리어싱/블러 없음
- [x] 힌트 없음/있음/fallback/충돌 규칙 일관 동작
- [x] CLI `pixelmaker extract <input> <output> --options` 실행 가능
- [x] MCP `extract_pixel_art` 툴 + 메타데이터 정상 반환
- [x] PNG 투명 배경, JPG, BMP, WebP 등 다양한 포맷 지원
- [x] 그레이스케일 입력 정상 처리
- [x] 4K+ 초고해상도 CI 시간/메모리 예산 내 처리
