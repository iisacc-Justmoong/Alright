<a id="finder-new-text"></a>

# 찾기 새 텍스트

이 문서는 0.3.0까지의 TXT·Swift 전환 기록이다. 0.4.0부터 메뉴는 `Alright` 하위 메뉴로 묶이고 10종 문서를 지원한다. 현재 구현은 [문서 생성](DocumentCreation.md)을 참조한다.

구현·실행 검증일: 2026-09-25. 환경: macOS 27.0 (26A428), Apple Silicon arm64, Swift 6.4 컴파일러·Swift 6 언어 모드, CMake 4.4.3·Ninja.

## 사용 동작

등록한 폴더와 하위 폴더의 **빈 공간 우클릭 → New Text**는 해당 위치에 0바이트 `New Text.txt`를 생성하고 기본 `.txt` 연결 앱으로 연다. 파일이 있으면 `New Text 2.txt`부터 비어 있는 이름을 선택한다. 내용, BOM, 개행을 쓰지 않으며 기존 파일을 덮어쓰지 않는다. 현재 컴퓨터의 기본 연결 앱은 `/System/Applications/TextEdit.app`으로 조회·실행 확인했다. TextEdit을 코드에 고정하지 않는다.

선택 파일·사이드바·검색 결과의 위치를 생성 폴더로 추측하지 않는다. 이번 메뉴는 Finder의 container 문맥에서만 제공한다. 등록 폴더 밖에서는 제공하지 않으며 전체 Finder 위치에서의 동작을 보장하지 않는다.

## Swift와 SF Symbols

호스트·Finder 확장·파일 생성·권한 저장소·기능 테스트를 Swift로 전환했다. C++/Objective-C++ 소스와 헤더는 제거했다. UI는 AppKit이고 공유 요청과 권한 저장은 Codable/PropertyList이다. 이전 `folders.plist`의 id·path·bookmark·device·inode를 그대로 읽으며 번들 ID·App Group·서명 팀도 유지한다.

앱 `.icns`, 화면 대표 아이콘, Finder New Text에는 `doc.badge.plus`를 사용한다. 설정·폴더 추가·등록 제거·Finder 열기는 `gearshape`, `folder.badge.plus`, `minus.circle`, `folder`이다. [Apple NSImage 시스템 심볼 API](https://developer.apple.com/documentation/appkit/nsimage/init(systemsymbolname:accessibilitydescription:))로 생성하며 별도 아이콘 폰트나 이미지 라이브러리를 요구하지 않는다.

## 권한과 프로세스

| 대상 | 권한·책임 |
| --- | --- |
| Alright 호스트 | App Sandbox, 사용자 선택 폴더 read-write, app-scoped security bookmark, App Group. 파일 생성과 기본 편집기 호출 |
| Finder Sync 확장 | App Sandbox와 동일 App Group. 감시 폴더의 메뉴를 제공하고 생성 요청 전달. 임의 사용자 파일 읽기·쓰기 권한 없음 |
| 공유 컨테이너 | `5U49ST9XZH.com.iisacc.Alright`. 등록 경로·호스트용 북마크와 일회성 요청 저장. 이 컨테이너 자체가 사용자 폴더 접근 권한을 부여하지 않음 |

앱의 `Add Folder…`는 macOS 표준 폴더 선택창으로 권한을 받고 보안 범위 북마크를 저장한다. 실행 시 해당 북마크를 해석하여 접근을 시작하고 사용 후 해제한다. 폴더 경로·inode·device를 재검증하며 이동·교체·만료가 확인되면 다시 등록하도록 안내한다. `Remove`는 등록을 없애고 확장의 감시 범위를 갱신한다. 별도 관리자 권한, 전체 디스크 접근, Apple Events, 손쉬운 사용 접근 권한은 요구하지 않는다.

현재 UI에서 확인한 등록 경로는 `/Users/ymy`와 `/Volumes/Storage/Workspace`이며 이번 에이전트의 생성 검증은 Workspace 아래에서만 수행했다. Desktop/Documents 등 추가 TCC 보호 영역, iCloud·SMB·외장 볼륨 재연결은 별도 검증 대상이다.

## 요청 안전성과 생성

1. 메뉴 생성 시 `targetedURL`을 스냅샷한다. Finder가 `representedObject`를 다른 프로세스로 전달하지 않는 실제 동작에 맞춰, 메뉴 `tag`와 확장 내부 스냅샷을 연결한다. 최대 64개의 최근 스냅샷을 보관한다.
2. 메뉴 선택 시 App Group에 UUID 요청을 기록하고 `alright://new-text/<UUID>`를 연다. URL에는 원시 경로나 실행 명령을 넣지 않는다.
3. 호스트는 Launch Services가 `didFinishLaunching` 전에 URL을 전달하는 경우도 처리하도록 저장소를 먼저 준비한다.
4. 공유 요청 파일을 원자적으로 `.processing`으로 바꿔 한 번만 소비한다. UUID·스키마·5분 만료·등록 폴더 ID를 확인한다. URL만 임의로 호출하거나 같은 요청을 재전송해도 새 파일을 만들지 않는다.
5. Swift/Darwin 생성부는 등록 폴더 descriptor에서 `openat`으로 하위 폴더를 연다. `..`·절대 하위 경로·심볼릭 링크 경유를 거절하고 `O_CREAT | O_EXCL`로 빈 TXT를 생성한다.
6. 기본 연결 앱을 `NSWorkspace`로 조회해 연다. 편집기 열기가 실패해도 이미 생성한 파일은 보존하고 생성 위치와 오류를 표시한다.

중단된 `.processing` 요청을 자동 재실행하지 않는다. 이는 중복 생성 방지를 위한 현재 계약이며 복사·이동용 복구 저널을 구현한 것은 아니다. 실행 중단 시 Finder에서 생성 여부를 확인한 뒤 새 요청을 실행한다.

## 빌드·등록

README의 CMake 빌드 후 `cmake --build build --target AlrightRegisterExtension`을 실행한다. 확장 경로는 `build/bin/Alright.app/Contents/PlugIns/AlrightFinderSync.appex`이며 별도 `.app`은 없다. 호스트와 확장은 동일한 기존 Developer ID 인증서로 서명했다. App Group은 Team ID 접두사 방식이며 별도 프로비저닝 프로필을 추가하지 않았다.

현재 개발 컴퓨터에서는 `pluginkit -a <appex>`와 `pluginkit -e use -i com.iisacc.Alright.FinderSync`로 등록·활성화를 확인했다. 사용자는 앱의 `Finder Extension Settings…`에서 활성화 상태를 관리할 수 있다. 재빌드 중 이미 실행 중인 확장의 이전 코드가 남는 경우 Alright 확장만 비활성화·재활성화한다. 이 작업에서 사용자 Finder 전체를 종료하지 않았다.

로컬 개발 빌드는 Developer ID 서명에 `--timestamp=none`을 사용한다. 공증·배포용 타임스탬프·배포 패키지 검증은 이번 완료 범위가 아니다.

## 검증

자동 테스트는 `ctest --test-dir build --output-on-failure`로 실행한다.

최종 실행 결과는 **5개 중 5개 통과**이다. `AlrightRegisterExtension` 타깃의 빌드·서명·등록도 성공했으며 이후 실제 Finder 동작을 다시 확인했다.

| 테스트 | 확인 내용 |
| --- | --- |
| AppLifecycle | 설정 창, 닫기·재열기, 위치·크기 보존, 표준 종료 메뉴, SF Symbols 로드 |
| NewText | 0바이트 TXT, 기존 내용 보존, 이름 충돌, 특수 문자, 경로 이탈·심볼릭 링크 거부, 동시 16건 생성 |
|요청| 이전 저장 형식 호환, 등록 경로 경계, 가장 구체적인 폴더 선택, 일회성 요청, 중복·위조 URL·만료·철회된 등록 거부 |
| FinderMenu | 빈 공간 문맥, 등록 밖·불명확한 대상 거부, Finder 메뉴 재구성 이후 tag로 원래 위치 유지, 중복 클릭 거부 |
|Bundle| 앱 하나, ICNS 해상도, 확장 메타데이터, 시스템 런타임만 참조, 양쪽 서명·Sandbox·동일 App Group, Swift 심볼·macOS 최소 버전 |

아래는 Swift 전환 이전 실제 검증 기록이며 당시 폴더는 `build/fixtures/finder-new-text/`이다.

- Finder 우클릭 메뉴의 `New Text` 노출을 스크린샷과 접근성 트리로 확인했다.
- 실제 메뉴 클릭으로 `New Text.txt` 생성, Finder의 `Zero bytes`, TextEdit의 같은 파일 URL과 빈 편집 영역을 확인했다.
- `⌘Q`로 호스트 프로세스가 없는 상태를 확인한 후 다시 메뉴를 클릭했다. 호스트가 자동 실행되어 `New Text 2.txt`를 생성하고 TextEdit에서 열었다.
- 원래 `New Text.txt`의 inode `24235565`와 0바이트 상태가 유지되었고, 두 번째 파일의 inode는 `24235655`이다.
- 북마크를 재사용한 호스트 재시작 후 생성도 확인했다. 메뉴 등록·활성화만으로 성공을 판정하지 않았다.
- 최종 메뉴 회귀 테스트 추가와 확장 재등록 뒤에도 호스트를 종료하고 실제 메뉴를 클릭했다. `New Text 3.txt`가 0바이트로 생성되어 TextEdit에서 열렸다.

증거는 `build/verification/finder-new-text-menu.png`, `build/verification/new-text-opened.png`, `build/verification/new-text-final-opened.png`, `build/verification/new-text-runtime.json`, `build/Testing/Temporary/LastTest.log`에 보관한다. build 산출물은 Git에서 제외한다.

## Swift 전환 후 실제 실행

Swift 호스트 0.3.0에서 기존 `/Users/ymy`, `/Volumes/Storage/Workspace` 등록과 확장 활성화 상태를 확인했다. 폴더 재선택 없이 기존 권한을 재사용했다. About 창에서 SF Symbol 기반 앱 아이콘과 버전 0.3.0 (3)을 확인했다.

2026-09-25 00:39–00:40 KST에 `build/fixtures/swift-finder/`의 실제 Finder 우클릭으로 검증했다.

- 호스트를 `⌘Q`로 종료하고 프로세스가 없음을 확인했다. 메뉴의 New Text를 클릭하자 Swift 호스트가 자동 실행되어 `New Text.txt`를 생성했다.
- Finder에서 Zero bytes, TextEdit에서 같은 파일 URL과 빈 편집 영역을 확인했다. 기본 연결 앱 조회 결과도 TextEdit이며 앱 구현에는 편집기를 고정하지 않았다.
- 두 번째 메뉴 클릭은 `New Text 2.txt`를 생성하고 열었다. 첫 파일은 0바이트와 inode `24242414`를 유지했다.
- 코드 서명 검사와 CTest 5개가 모두 통과했다. 최소 타깃은 macOS 14.0이나 실제 실행 검증 환경은 macOS 27.0 arm64이다.

Swift 증거: `build/verification/swift-host.png`, `swift-about-icon.png`, `swift-finder-menu.png`, `swift-text-opened.png`, `swift-second-text-opened.png`, `swift-runtime.json`. 테스트 로그는 `build/Testing/Temporary/LastTest.log`이다. 산출물은 Git에서 제외한다.

## 공식 API 근거

- [Apple Finder Sync guide](https://developer.apple.com/library/archive/documentation/General/Conceptual/ExtensibilityPG/Finder.html): 등록 디렉터리의 문맥 메뉴, container 문맥, `targetedURL`의 유효 시점, 공유 컨테이너.
- [Apple App Groups entitlement](https://developer.apple.com/documentation/BundleResources/Entitlements/com.apple.security.application-groups): 동일 팀의 공유 컨테이너와 macOS Team ID 접두사.
- [Apple app group container access](https://developer.apple.com/documentation/xcode/accessing-app-group-containers): Team ID 접두사 그룹은 macOS에서 프로비저닝 프로필 없이 동일 서명 팀으로 검증한다.
