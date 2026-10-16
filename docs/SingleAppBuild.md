# 단일 앱 빌드

Alright의 canonical 앱은 `build/bin/Alright.app`이다. 모든 구성은 이 경로를 공유하고 테스트는 일반 실행 파일로 생성한다. 빌드 디렉터리는 프로젝트의 `build/`로 고정한다. 여러 구성을 동시에 빌드하지 않는다.

`cmake/single-app/`은 Product 공통 정책의 복사본이다. `Defaults.cmake`를 `project()` 전에 읽고 `product_single_app`을 지연 호출하여 컴파일러 검사와 테스트가 추가 `.app`을 생성하지 않게 한다. 독립 체크아웃에서도 상위 Product 디렉터리 없이 빌드 가능하다.

Swift 6 소스는 CMake의 Ninja 생성기로 빌드한다. macOS 시스템 프레임워크와 시스템 Swift 런타임만 동적으로 참조한다. 최소 OS는 Swift 컴파일 타깃과 Info.plist 모두 macOS 14.0으로 지정한다. Finder 확장은 canonical 앱의 `Contents/PlugIns/AlrightFinderSync.appex`에 직접 빌드한다. `AlrightBundle` 기본 빌드 타깃이 확장 → 호스트 순서로 같은 팀의 앱 인증서를 사용하여 서명한다.

`ALRIGHT_APP_STORE=OFF`인 직접 배포 모드는 Developer ID Application 서명을 사용한다. Finder 확장은 Sandbox를 유지하고 호스트는 접근성 권한으로 Finder 이름 편집을 자동으로 시작한다. 로컬 개발 단계의 서명은 공증 완료를 뜻하지 않는다. `ALRIGHT_APP_STORE=ON`인 App Store 모드는 Apple Distribution 서명과 양쪽 번들의 Sandbox를 요구하며 접근성 설정·권한 요청·AX 이름 편집 경로를 사용하지 않는다. 생성한 파일을 `NSWorkspace.activateFileViewerSelecting`으로 Finder에서 선택하고 Return으로 이름을 편집하도록 안내한다. 모드별 값은 CMake가 생성한 `BuildConfiguration.appStore`로 전달한다.

서명이 필요한 실행 산출물은 `cmake --build build` 또는 `cmake --build build --target AlrightBundle`로 생성한다. `Alright` 개별 타깃은 링크 단계만 수행하므로 실행·검증 전 `AlrightBundle`을 빌드한다. 재등록은 `cmake --build build --target AlrightRegisterExtension`으로 수행한다. 이 타깃은 서명 후 Launch Services와 pluginkit에 등록하며 확장 활성화 여부는 시스템 설정에서 유지한다.

패키지나 테스트를 위한 앱 복사본은 만들지 않는다. App Store `.pkg`는 canonical 앱에서 직접 생성하여 `build/appstore/`에 둔다. 앱의 Apple Distribution 서명과 별개로 패키지에는 Mac Installer Distribution 서명이 필요하다. 명령과 검증 범위는 [App Store 배포](AppStoreDistribution.md)에 기록한다. App Store 서명 산출물은 업로드용이며 로컬 실행 검증은 개발 서명으로 같은 Sandbox 모드를 검증한다. 로컬 서명 검사만으로 App Store 업로드·심사·설치 완료를 뜻하지 않는다.

CTest의 `Alright.Bundle`이 `.app` 개수, 번들 식별자, 시스템 라이브러리 의존성, 호스트·확장 서명, `CMakeCache.txt`의 `ALRIGHT_APP_STORE`에 따른 호스트 Sandbox와 확장의 Sandbox, 양쪽 서명 팀·동일 App Group, App Store 모드의 Apple Distribution 서명, ICNS 해상도, Mach-O 최소 OS·Swift 심볼, 번들 실행 폴더의 불필요한 산출물 부재를 검사한다. `Alright.AppLifecycle`은 직접 배포 모드의 이름 편집 설정 버튼 유지, App Store 모드의 해당 버튼 부재·접근성에 의존하지 않는 준비 상태·수동 Return 안내와 기존 단일 창 수명주기를 검사한다.

앱 아이콘의 편집 원본은 `resources/AppIcon/Alright.ai`이며 같은 디렉터리에 SVG 벡터 사본과 Illustrator에서 내보낸 `Alright.png` 마스터를 보관한다. PNG는 1024×1024 픽셀의 불투명한 정사각형이고, 배경이 가장자리까지 채워지며 외곽 보더나 투명 여백이 없다. `tools/GenerateIcon.swift`가 이 마스터를 16·32·128·256·512 포인트의 1배·2배, 총 10개 PNG로 리샘플링하고 `iconutil`로 `build/generated/Alright.icns`를 생성한다. 1024픽셀 표현은 마스터 PNG를 그대로 사용한다. CMake가 마스터 변경을 추적하므로 Illustrator에서 PNG를 다시 내보내고 빌드하면 서명 전에 canonical 앱 Resources의 ICNS가 갱신된다. `Alright.Bundle`은 PNG 마스터의 크기·모든 픽셀의 불투명도, 생성된 10개 PNG의 크기·불투명도, 마스터와 최대 해상도 표현의 일치, 생성 ICNS와 번들 ICNS의 동일성을 검증한다.

Finder 사이드바 아이콘은 호스트의 `resources/Info.plist.in`에서 `CFBundleIcons → CFBundlePrimaryIcon → CFBundleSymbolName = folder`로 지정한다. [Apple의 SF Symbol 번들 설정](https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleicons/cfbundleprimaryicon/cfbundlesymbolname)을 사용하며, Workspace 같은 등록 폴더는 Finder 사이드바에서 네이티브 폴더 심벌로 표시된다. `Alright.Bundle`은 배포 번들의 `folder` 선언과 기존 앱 ICNS 검사를 함께 수행한다. 실제 반영은 확장이 활성화된 Finder에서 폴더 아이콘과 Alright 우클릭 메뉴를 모두 확인한다.

도구와 테스트는 일반 실행 파일이다. Swift 모듈은 `build/modules/`, 디버그 심볼은 `build/symbols/`, 컴파일 의존성 파일은 `build/CMakeFiles/`에 둔다. Swift 드라이버가 Release 링크 시 번들의 `Contents/MacOS/`에 생성하는 `Alright.d`와 `AlrightFinderSync.d`도 서명 전에 `build/CMakeFiles/*swift-link.d`로 이동한다. 실행 파일 디렉터리에 `.d`나 `.dSYM`이 남으면 `Alright.Bundle`이 실패한다.

공통 정책 변경 시 Workspace에서 `python3 -B Product/build-policy/sync.py`를 실행한다. 전체 감사는 `python3 -B Product/build-policy/audit.py --report Product/build-policy/build/audit.json`으로 수행한다.
