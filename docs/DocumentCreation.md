# Alright 문서 생성

2026-09-25 · 버전 0.6.1 · Swift 6 · macOS 전용

**우클릭 → Alright → 파일 생성 → Finder에서 제목 입력.format**으로 끝난다. 생성 후 기본 앱이나 Adobe 앱을 실행하지 않는다. Finder가 파일명 본문을 선택하고 확장자를 유지한 채 이름 편집 상태가 된다. Return으로 이름을 확정한다. 같은 이름이 존재하면 초기 파일명에 ` 2`, ` 3`을 붙이며 기존 파일을 덮어쓰지 않는다.

| 메뉴 | 형식 | 초기 문서 |
| --- | --- | --- |
| New Text | `.txt` | 0바이트 |
| New Markdown | `.md` | 0바이트 |
| New Rich Text | `.rtf` | 빈 서식 문서 |
| New PDF | `.pdf` | A4 세로 빈 페이지 1개 |
| New Word Document | `.docx` | A4 세로 빈 본문 |
| New Excel Workbook | `.xlsx` | 빈 Sheet1, A1 선택 |
| New PowerPoint Presentation | `.pptx` | 16:9 빈 슬라이드 1개 |
| New OpenDocument Text | `.odt` | A4 세로 빈 본문 |
| New OpenDocument Spreadsheet | `.ods` | 빈 Sheet1 |
| New OpenDocument Presentation | `.odp` | 16:9 빈 슬라이드 1개 |
| New JSON | `.json` | 빈 객체 `{}`와 개행 |
| New CSV | `.csv` | 빈 CSV, 0바이트 |
| New HTML | `.html` | UTF-8·viewport 메타데이터와 빈 body |
| New SVG | `.svg` | 1920×1080 빈 SVG 캔버스 |
| New Photoshop Document | `.psd` | 우클릭한 화면 크기, RGB 8비트, 72ppi, 투명 Layer 1 |
| New Illustrator Document | `.ai` | 우클릭한 화면 크기, RGB, 아트보드 1개, 빈 Layer 1 |

## 메뉴 아이콘

Alright 그룹과 문서 16종은 SF Symbols를 사용한다. 메뉴가 요청될 때 현재 모양의 `NSColor.labelColor`로 단색 이미지를 만들고 템플릿 속성도 유지한다. macOS 27의 Finder에서 원본 SF Symbol과 `isTemplate`만 전달하면 검은색으로 표시되므로, 프로세스 간 전달 과정에서 템플릿 정보가 적용되지 않아도 글자 계열 색상이 유지되도록 픽셀에 반영한다. 색상을 고정된 흰색으로 지정하거나 이전 메뉴의 이미지를 캐시하지 않는다. Finder가 템플릿을 적용하지 않는 경우 선택 강조 시에도 메뉴를 열 때 계산한 아이콘 색상이 유지된다.

SVG·Illustrator는 실제 지원되는 `point.topleft.down.to.point.bottomright.curvepath`를 사용한다. 존재하지 않는 `bezier.path`에 의한 Finder 기본 `+` 아이콘을 제거했다. FinderMenu 테스트는 그룹·16종 아이콘과 밝은 모드·어두운 모드·각 고대비 모드에서 TIFF 전달 후의 실제 픽셀 색상·비어 있지 않은 심볼을 검증한다. 실제 Finder 메뉴 확인 자료는 `build/verification/menu-icons/`에 보관한다.

## 화면 크기

Finder 메뉴를 구성하는 순간 포인터가 속한 NSScreen의 전체 frame × backingScaleFactor를 정수 픽셀로 저장한다. Dock·메뉴 막대를 뺀 작업 영역이 아니라 전체 화면 기준이다. 다중 모니터에서는 우클릭한 화면을 사용하며, 요청 처리 중 포인터를 다른 화면으로 옮겨도 캡처한 크기를 유지한다. Retina·화면 회전·비정형 너비를 지원한다. PSD와 AI에는 같은 크기가 기록된다. 표시 장치가 없는 예외 환경만 1920×1080을 사용한다. 각 축 1–16383 픽셀을 허용하며 범위 밖 크기를 조용히 축소하지 않고 오류로 처리한다.

## 문서 형식

Office 6종은 [Office 문서 생성](OfficeDocuments.md)에 원본 XML 구조·빌드 패키징·검증 절차를 기록한다. Microsoft Office와 OpenDocument 항목 사이에 구분선을 두며 기존과 같은 Alright 하위 메뉴에서 바로 선택한다.

PSD는 `PhotoshopDocument.swift`가 [Adobe Photoshop 파일 형식 명세](https://www.adobe.com/devnet-apps/photoshop/fileformatashtml/)에 따라 매번 생성한다. PSD 버전 1의 레이어·RGBA 채널·PackBits 압축·72ppi 리소스를 포함한다. 폭이 128의 배수가 아니어도 마지막 run을 올바르게 기록한다.

AI는 Illustrator 2026에서 저장한 **압축하지 않은 Illustrator 2020 호환·PDF 호환·ICC 프로필 포함** 빈 문서의 편집 스트림을 사용한다. `IllustratorDocument.swift`가 native artboard 좌표와 cropmarks를 새 크기로 변경하고, 동일한 크기의 PDF 페이지와 올바른 xref·스트림 길이를 작성한다. 일반 PDF를 AI로 이름만 바꾸는 방식이 아니다. Adobe 실행이나 Apple Events 자동화 없이 생성한다.

원본 템플릿을 갱신할 때는 Illustrator에서 빈 RGB 1920×1080 문서를 위 설정으로 저장한 뒤 실행한다.

```sh
python3 tools/ExtractIllustratorTemplate.py build/blank-uncompressed.ai resources/DocumentTemplates
cmake --build build
ctest --test-dir build --output-on-failure
```

`Blank.aiprivate`와 `Blank.aimetadata`가 실행 시 사용하는 리소스이다. 과거 고정 크기 `Blank.ai`, `Blank.psd`, `GeneratePSDTemplate.swift`는 0.4.0의 원본 기록이며 현재 생성 경로에서는 사용하지 않는다.

## 권한과 처리 흐름

Finder 이름 편집에는 macOS 접근성(최신 OS의 Device Control and Data Access) 권한이 필요하다. 최초 설정 화면의 **Enable Filename Editing…**에서 설정한다. Finder 확장은 App Sandbox를 유지한다. 다른 앱의 UI에 접근하는 호스트는 App Sandbox 밖에서 실행하며 Developer ID 서명과 hardened runtime을 유지한다. 등록 폴더·북마크·device/inode 검증과 경로 이탈 차단은 그대로 적용한다. 전체 디스크 접근이나 Adobe 자동화 권한은 사용하지 않는다.

- `FolderStore.swift`: 요청 버전 3으로 문서 종류·화면 크기·대상 경로를 전달한다. 버전 1·2 요청 호환, 만료·중복·유효하지 않은 크기 거부를 유지한다.
- `FinderSync.swift`: 각 메뉴의 경로·종류·화면 크기를 tag로 보존하며 호스트는 활성화하지 않고 호출한다.
- `DocumentCreator.swift`: 숨김 임시 파일에 전체 내용을 기록·fsync 후 `renameatx_np(RENAME_EXCL)`로 게시한다. 오류 시 임시 파일을 정리한다.
- `DocumentService.swift`: 등록 경로와 파일 권한을 검증하고 문서 생성만 수행한다.
- `FinderRenamer.swift`: Finder에 파일을 표시한 뒤 **실제로 단일 선택된 파일 URL이 생성 파일과 일치하는지** 확인한다. Finder의 Rename 메뉴를 접근성 API로 누른 뒤 이름 편집 포커스를 확인하고 종료한다. 무조건적인 Return 키 입력·편집기 열기는 없다. 다른 선택을 감지하면 이름 변경 명령을 실행하지 않는다.
- `AppDelegate.swift`: URL로 시작한 경우 설정 창을 표시하지 않고 요청을 직렬 처리한다. 일반 앱 실행·재열기에는 설정 창을 보여준다.

권한이 없으면 설정 안내를 표시하며 파일 생성 전에 중단한다. 파일 생성 후 Finder 응답에 실패하면 파일은 보존하고 오류를 표시한다.

## 검증

CTest 7개는 TXT 충돌·동시 생성·경로 이탈, 16종 생성, Office ZIP·XML·관계·빈 문서 구조, PSD ImageIO 디코딩, AI PDF/native 크기 일치, 5120×2880·1513×983·1080×1920·1×1 생성과 잘못된 크기 거부, 요청 프로토콜, 메뉴 전달, 앱 수명주기, 단일 앱·서명을 검증한다. `build/verification/rename/status.json`에 이름 편집의 실제 검증 상태를, `build/verification/office/`에 Office 검증 기록을 보관한다. 접근성 권한이 꺼진 현재 개발 컴퓨터에서 이름 편집의 실기기 검증은 미완료이다.
