# Hello World 호스트 앱

이 문서는 2026-09-24의 최초 구현 기록이다. 2026-09-25부터 현재 화면과 기능은 [Finder New Text](FinderNewText.md)로 발전했으며 아래 미구현 항목·ad-hoc 서명 설명은 당시 상태이다.

2026-09-24 구현. 기존 Finder 유틸리티 청사진의 AppKit 호스트를 실행 가능한 최소 앱으로 구성하였다.

## 구현 범위

- C++23·Objective-C++와 AppKit, ARC 메모리 관리.
- Alright 창과 `Hello World`, `Right where you click.` 표시.
- 창 닫기 후 프로세스 유지, Dock/Finder 재열기, 동일 창의 위치·크기 유지.
- About, Hide, Quit, Show Alright, Minimize, Close 표준 메뉴.
- 단일 앱 빌드, 로컬 ad-hoc 서명, 외부 런타임 없는 실행.

Finder Sync 확장, 파일 생성·복사·이동, 권한 등록, 설정 저장, 배포용 서명·공증은 후속 작업이다. G0와 제품 인수 테스트 A01–A15는 이번 Hello World 완료와 별개이다. 재사용할 파일 작업 로직이 없는 단계이므로 빈 SDK·core 계층을 추가하지 않았다.

## 자동 검증

`ctest --test-dir build --output-on-failure`를 실행한다.

| 테스트 | 검증 내용 |
| --- | --- |
| `Alright.AppLifecycle` | 실제 AppKit 창 생성, Hello World 라벨, 닫기·재열기, 창 객체·위치·크기 보존, 표준 종료 메뉴 |
| `Alright.Bundle` | build 전체에 앱 한 개, Info.plist, 실행 파일, 시스템 라이브러리만 참조, 서명 유효성 |

AppLifecycle 테스트는 로그인한 macOS GUI 세션에서 실행하며 테스트 중 창이 잠시 표시된다. 실제 앱의 Launch Services 실행과 키보드 종료는 별도 수동 검증 대상이다.

## 실제 실행 기록

검증 환경: macOS 27.0 (26A428), Apple Silicon arm64, AppleClang 21.0.0, CMake 4.4.3, Debug 빌드. macOS 14.0은 빌드 최소 대상이며 해당 버전 실기기 검증 결과는 아니다.

- CMake 구성·빌드 성공, 마지막 빌드에 컴파일 경고 없음.
- CTest 2/2 통과: AppLifecycle, Bundle.
- Product 정책 복사본 일치 테스트 1개와 감사 도구 회귀 테스트 3개 통과.
- canonical 경로에서 실행한 실제 창의 접근성 트리와 스크린샷으로 Hello World 표시 확인.
- 실제 `⌘W` 입력 후 화면에 Alright 창이 없고 프로세스 PID 19798은 유지됨을 확인.
- 앱 재열기 후 Hello World 창 표시와 같은 PID 19798 유지 확인.
- 실제 `⌘Q` 입력 후 프로세스 종료 확인. 검증 후 앱을 다시 실행해 둠.
- 별도 AppKit 자동 테스트에서 창 위치·크기 변경 후 닫기·재열기 보존 확인.

재생성 가능한 로컬 증거: `build/verification/hello-world.png`, `build/verification/bundle-audit.json`, `build/Testing/Temporary/LastTest.log`. build 산출물은 Git에서 제외한다.
