# 단일 앱 빌드

Alright의 canonical 앱은 `build/bin/Alright.app`이다. 모든 구성은 이 경로를 공유하고 테스트는 일반 실행 파일로 생성한다. 빌드 디렉터리는 프로젝트의 `build/`로 고정한다. 여러 구성을 동시에 빌드하지 않는다.

`cmake/single-app/`은 Product 공통 정책의 복사본이다. `Defaults.cmake`를 `project()` 전에 읽고 `product_single_app`을 지연 호출하여 컴파일러 검사와 테스트가 추가 `.app`을 생성하지 않게 한다. 독립 체크아웃에서도 상위 Product 디렉터리 없이 빌드 가능하다.

Swift 6 소스는 CMake의 Ninja 생성기로 빌드한다. macOS 시스템 프레임워크와 시스템 Swift 런타임만 동적으로 참조한다. 최소 OS는 Swift 컴파일 타깃과 Info.plist 모두 macOS 14.0으로 지정한다. Finder 확장은 canonical 앱의 `Contents/PlugIns/AlrightFinderSync.appex`에 직접 빌드한다. `AlrightBundle` 기본 빌드 타깃이 확장 → 호스트 순서로 같은 Developer ID 인증서를 사용하여 서명한다. 로컬 개발 단계에서는 타임스탬프를 생략하며 공증 완료를 뜻하지 않는다.

서명이 필요한 실행 산출물은 `cmake --build build` 또는 `cmake --build build --target AlrightBundle`로 생성한다. `Alright` 개별 타깃은 링크 단계만 수행하므로 실행·검증 전 `AlrightBundle`을 빌드한다. 재등록은 `cmake --build build --target AlrightRegisterExtension`으로 수행한다. 이 타깃은 서명 후 Launch Services와 pluginkit에 등록하며 확장 활성화 여부는 시스템 설정에서 유지한다.

패키지나 테스트를 위한 앱 복사본은 만들지 않는다. CTest의 `Alright.Bundle`이 `.app` 개수, 번들 식별자, 시스템 라이브러리 의존성, 호스트·확장 서명, 양쪽 Sandbox 및 동일 App Group, ICNS 해상도, Mach-O 최소 OS·Swift 심볼, 번들 실행 폴더의 불필요한 산출물 부재를 검사한다.

SF Symbols `doc.badge.plus`를 `tools/GenerateIcon.swift`가 10개 PNG 해상도로 렌더링하고 `iconutil`로 `build/generated/Alright.icns`를 생성한다. 서명 전에 canonical 앱 Resources로 배치한다. 도구와 테스트는 일반 실행 파일이다. Swift 모듈은 `build/modules/`, 디버그 심볼은 `build/symbols/`, 컴파일 의존성 파일은 `build/CMakeFiles/`에 둔다.

공통 정책 변경 시 Workspace에서 `python3 -B Product/build-policy/sync.py`를 실행한다. 전체 감사는 `python3 -B Product/build-policy/audit.py --report Product/build-policy/build/audit.json`으로 수행한다.
