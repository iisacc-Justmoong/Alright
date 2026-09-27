# Office 문서 생성

0.6.0에서 6종을 추가했다. 생성 후 앱을 실행하지 않고 Finder 이름 편집으로 끝나는 기존 흐름을 공유한다. 파일 생성에는 Office 계정·설치·네트워크가 필요하지 않다.

| 형식 | 초기 내용 | 구조 |
| --- | --- | --- |
| DOCX | 빈 문단, A4 세로, 2.54cm 여백 | WordprocessingML 문서·스타일 |
| XLSX | Sheet1 1개, 데이터 없음, A1 선택 | SpreadsheetML 통합 문서·워크시트·기본 스타일 |
| PPTX | 16:9 빈 슬라이드 1개 | PresentationML 슬라이드·마스터·빈 레이아웃·테마 |
| ODT | 빈 문단, A4 세로, 2.54cm 여백 | OpenDocument 1.3 text |
| ODS | 빈 Sheet1 1개 | OpenDocument 1.3 spreadsheet |
| ODP | 16:9 빈 슬라이드 1개 | OpenDocument 1.3 presentation |

## 유지보수

`resources/OfficeTemplates/<확장자>/`의 XML 파일이 원본이다. 검토 가능한 일반 텍스트로 관리하며 `tools/BuildOfficeTemplates.py`가 빌드 시 결정적인 ZIP 파일을 만든다. `build/generated/OfficeTemplates/Blank.*`를 유일한 앱의 `Contents/Resources/DocumentTemplates`에 복사한 뒤 코드 서명한다. Python 표준 라이브러리만 빌드에 필요하며 실행 시에는 Swift가 포함된 문서를 읽어 파일을 생성한다.

OpenDocument의 mimetype 항목은 첫 번째 ZIP 엔트리로 압축·추가 필드 없이 저장한다. OOXML의 Content Types와 관계 파일은 문서 종류에 맞게 선언한다. 매크로, 외부 링크, 예제 데이터, 개인 메타데이터를 포함하지 않는다. 새 형식을 추가하면 DocumentKind의 안정적인 식별자·메뉴 이름·SF Symbol과 테스트·문서를 함께 갱신한다.

규격 참고: [Microsoft OOXML 패키지](https://learn.microsoft.com/en-us/office/open-xml/general/how-to-create-a-package), [PresentationML 구조](https://learn.microsoft.com/en-us/office/open-xml/presentation/structure-of-a-presentationml-document), [OASIS OpenDocument 1.3 패키지](https://docs.oasis-open.org/office/OpenDocument/v1.3/OpenDocument-v1.3-part2-packages.html).

## 검증

```sh
cmake -S . -B build -G Ninja
cmake --build build
ctest --test-dir build --output-on-failure
```

- Swift 생성 경로로 각 형식을 만들고 이름 충돌 시 기존 파일을 보존하는지 검증한다. 요청 전달과 Finder 메뉴의 16종 항목·아이콘을 검사한다.
- `Alright.OfficePackages`는 Swift가 생성한 파일을 Python zipfile·ElementTree로 읽어 CRC, XML, OOXML 참조 무결성, 빈 문서·시트·슬라이드 개수, ODF MIME·manifest를 검증한다.
- 별도 독립 읽기: python-docx, openpyxl, python-pptx로 DOCX·XLSX·PPTX를 해석했다. 세 OpenDocument 형식은 OASIS ODF 1.3 RelaxNG와 manifest 스키마를 통과했다. 이 추가 도구들은 배포·빌드 필수 의존성이 아니다.
- XLSX를 설치된 Microsoft Excel에서 실제 열어 복구 경고 없이 빈 Sheet1과 A1 상태를 확인했다. DOCX·PPTX의 빈 문서 미리보기도 macOS Quick Look으로 확인했다.
- 실제 Finder의 Alright 하위 메뉴에서 16종 항목과 SF Symbol을 확인했다. `finder-menu.txt`, `finder-menu.png`, `runtime.json`에 증거를 남겼다.
- Finder의 파일명 편집은 앞서 구현한 접근성 권한이 필요하다. 해당 권한은 현재 개발 컴퓨터에서 꺼져 있으므로 전체 우클릭→생성→이름 편집의 실제 검증은 대기 상태이다. 새 형식의 생성·파일 구조 검증과 구분한다.

증거 디렉터리: `build/verification/office/`. Windows Office와 LibreOffice에서의 직접 실행은 이번 검증 범위에 포함하지 않는다.
