# Alright

**Finder에서 파일을 만드는 순간부터 정리하는 순간까지, 필요한 작업을 우클릭으로 끝내는 macOS 유틸리티이다.**

브랜드 문구 초안: **Alright. Right where you click.**

현재는 **Finder 빈 공간 우클릭 → Alright → 파일 생성 → Finder에서 제목 입력**으로 끝나는 macOS 전용 앱이다. TXT·Markdown·RTF·PDF·DOCX·XLSX·PPTX·ODT·ODS·ODP·JSON·CSV·HTML·SVG·Photoshop PSD·Illustrator AI의 16종을 지원한다. Swift 6·AppKit·Finder Sync로 구성하며 Qt와 외부 런타임을 요구하지 않는다. 앱·화면·메뉴 아이콘은 SF Symbols를 사용한다.

## 빌드와 실행

macOS, Swift 6을 제공하는 Xcode, CMake 3.24 이상, Ninja, Python 3과 유효한 macOS 코드 서명 인증서가 필요하다. Python 표준 라이브러리는 빌드 시 Office 문서를 패키징하고 테스트하는 데만 사용한다. 배포 앱은 Python·Office·LibreOffice 설치 없이 파일을 생성한다. 프로젝트 디렉터리에서 실행한다.

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build --output-on-failure
cmake --build build --target AlrightRegisterExtension
open build/bin/Alright.app
```

기존 Unix Makefiles 빌드 트리를 전환할 때에는 최초 한 번 `cmake --fresh -S . -B build -G Ninja`를 실행한다. Swift 모듈·디버그 심볼·아이콘 생성 중간 파일도 모두 `build/`에 둔다.

기본 서명 설정은 로컬에 보유한 `Developer ID Application: MUYEONG YUN (5U49ST9XZH)`이다. 다른 개발 환경에서는 CMake의 `ALRIGHT_SIGNING_IDENTITY`와 `ALRIGHT_TEAM_ID`를 함께 지정한다. 동일 팀의 앱과 확장이 공유 컨테이너를 사용하므로 ad-hoc 서명으로 대체하지 않는다.

1. `Finder Extension Settings…`에서 Alright 확장을 켠다. 현재 개발 컴퓨터에서는 등록·활성화를 완료했다.
2. `Add Folder…`로 사용할 폴더를 선택하여 읽기·쓰기 권한을 부여한다. 선택한 폴더와 하위 폴더가 적용 대상이다.
3. `Enable Filename Editing…`에서 Finder 이름 편집에 필요한 macOS 접근성 권한을 설정한다.
4. Finder에서 해당 폴더를 열고 **빈 공간을 우클릭 → Alright → 원하는 문서 종류**를 선택한다.
5. 파일이 생성되고 Finder에서 이름을 입력하는 상태가 된다. 이름이 이미 있으면 ` 2`, ` 3`을 붙인다. TXT는 0바이트이며 PSD·AI는 우클릭한 화면의 픽셀 크기로 생성한다. 편집기를 자동으로 열지 않는다. 형식별 초기 내용은 [문서 생성](docs/DocumentCreation.md)에 명시한다.

`Remove`는 폴더 등록과 앱이 저장한 접근 권한을 제거한다. 사용자 파일은 삭제하지 않는다. 창 닫기 또는 `⌘W`는 창만 닫고, `⌘Q`는 앱을 종료한다. 앱이 종료되어 있어도 활성화된 Finder 확장의 New Text 요청으로 다시 실행된다.

유일한 앱 산출물은 `build/bin/Alright.app`이며 Finder 확장은 내부 `Contents/PlugIns/AlrightFinderSync.appex`이다. Developer ID 서명과 hardened runtime을 적용한다. Finder 확장은 App Sandbox를 유지하며 호스트는 Finder 이름 편집을 위해 접근성 권한을 사용한다. 로컬 빌드는 타임스탬프·공증을 생략한다. 전체 디스크 접근·Apple Events 자동화 권한을 요구하지 않는다. 현재 동작과 제약은 [문서 생성](docs/DocumentCreation.md)에 명시한다.

| 문서 | 내용 |
| --- | --- |
| [제품·기술 청사진](docs/BLUEPRINT.md) | 사용자, 기능 범위, 우클릭 구조, 네이티브 아키텍처, SDK 활용, 수익화 |
| [실행·검증 계획](docs/DELIVERY.md) | 기술 실증, 구현 순서, 인수 기준, 실패 처리, 출시 관문 |
| [Finder New Text 구현](docs/FinderNewText.md) | 권한·확장 구조, 테스트, 실제 Finder 실행 증거 |
| [다양한 문서 생성](docs/DocumentCreation.md) | Alright 하위 메뉴, 16종 형식, 화면 크기, Finder 이름 편집 |
| [Office 문서 생성](docs/OfficeDocuments.md) | DOCX·XLSX·PPTX·ODT·ODS·ODP, XML 원본과 패키징·검증 |
| [Hello World 구현](docs/HelloWorld.md) | 최초 호스트 앱 구현의 과거 검증 기록 |
| [단일 앱 빌드](docs/SingleAppBuild.md) | 산출물 경로, 재빌드·서명 규칙 |

## 핵심 결정

- 제품은 macOS 전용 Finder 확장이다. 파일 생성, 경로 복사, 목적지 지정 복사·이동을 중심으로 한다.
- Finder Sync의 적합성·노출 범위·권한 전달을 먼저 실증한다. 모든 폴더에서의 동작을 미리 보장하지 않는다.
- 파일 생성·권한 저장·AppKit UI·Finder Sync 확장을 Swift 6으로 구현한다. Qt 의존성은 도입하지 않는다.
- 계정과 서버 없이 기본 파일 작업이 동작한다. 유료 기능·가격은 검증할 사업 가설이다.
- 등록 폴더에서 문서를 생성한다. 0.5.0부터는 Finder 이름 편집으로 끝난다. PSD·AI 형식은 Photoshop·Illustrator로 확인한다. 경로 복사·파일 복사·이동은 후속 범위이다.

청사진 작성일: 2026-09-20. Swift 전환일: 2026-09-25. 기술 문서로 확인한 사실과 제품 설계 가설, 미검증 항목을 각 문서에서 구분한다.
