# TestFlight 프로비저닝 프로파일

macOS TestFlight 배포 후보는 호스트 앱과 Finder Sync 확장 각각의 Mac App Store 배포 프로비저닝 프로파일을 포함한다. 일반 Mac App Store 배포는 제한된 entitlement를 사용하지 않으면 프로파일 없이 가능하지만, TestFlight는 프로파일을 요구한다. 이는 [Apple TN3125: Inside Code Signing: Provisioning Profiles](https://developer.apple.com/documentation/technotes/tn3125-inside-code-signing-provisioning-profiles)의 macOS 및 TestFlight 규칙이다.

프로파일은 Apple Developer 포털에서 명시적 App ID `com.iisacc.Alright` 및 `com.iisacc.Alright.FinderSync`에 대해 발급한다. 두 프로파일의 팀과 허용 인증서는 실제 앱·확장의 Apple Distribution 서명과 일치해야 한다. 이 프로젝트의 Team ID와 App ID prefix는 `5U49ST9XZH`이다. 프로파일 원문 및 인증서·계정 자격 증명을 소스 저장소에 추가하지 않는다.

저장소 루트에서 다음과 같이 명시적으로 프로파일 경로를 지정한다. 다운로드한 프로파일은 해당 프로젝트의 `build/signing/`에 둔다. 확장 프로파일 파일명은 아래 예시 또는 실제 다운로드 파일 경로를 사용한다.

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DALRIGHT_APP_STORE=ON \
  -DALRIGHT_SIGNING_IDENTITY='Apple Distribution: MUYEONG YUN (5U49ST9XZH)' \
  -DALRIGHT_HOST_PROVISION_PROFILE="$PWD/build/signing/Alright-Mac-AppStore.provisionprofile" \
  -DALRIGHT_EXTENSION_PROVISION_PROFILE="$PWD/build/signing/Alright-FinderSync-Mac-AppStore.provisionprofile"
cmake --build build
ctest --test-dir build --output-on-failure
cmake --build build --target AlrightAppStorePackage
```

`ALRIGHT_HOST_PROVISION_PROFILE`과 `ALRIGHT_EXTENSION_PROVISION_PROFILE`은 `ALRIGHT_APP_STORE=ON`에서만 사용하며 둘 다 지정하거나 둘 다 생략한다. CMake 구성은 두 경로가 실제 파일인지 확인한다. 빌드할 때 호스트 프로파일은 canonical `build/bin/Alright.app/Contents/embedded.provisionprofile`에, 확장 프로파일은 `build/bin/Alright.app/Contents/PlugIns/AlrightFinderSync.appex/Contents/embedded.provisionprofile`에 포함한다. 생성된 각각의 entitlement에는 명시적 `com.apple.application-identifier`와 `com.apple.developer.team-identifier`를 추가하고 프로파일 포함 후 확장 → 호스트 순서로 서명한다. 앱 복사본은 만들지 않는다.

프로파일 없이 일반 Store 구성을 만들려면 기존 CMake 캐시의 두 경로를 빈 값으로 지운다.

```sh
cmake -S . -B build -DALRIGHT_APP_STORE=ON \
  -DALRIGHT_HOST_PROVISION_PROFILE= -DALRIGHT_EXTENSION_PROVISION_PROFILE=
cmake --build build
```

다음 번들 빌드는 이전에 포함한 `embedded.provisionprofile`을 양쪽에서 제거한 뒤 현재 구성을 서명한다. 직접 배포 구성으로 바꿀 때도 두 경로를 빈 값으로 설정하며, 해당 구성이 사용하는 Developer ID Application 신원을 명시한다. 프로파일 파일 자체는 `build/signing/`에서 제거하지 않는다.

패키지 도구는 프로파일이 존재하면 양쪽 모두 존재하는지 확인하고 `security cms -D -i`로 읽는다. native macOS 플랫폼, 동일 팀·App ID prefix, 각 번들의 명시적 App ID, 실제 leaf 서명 인증서 SHA-256, 만료 및 유효 시작 시각, 개발 장치 목록이나 Developer ID의 전체 장치 프로비저닝 부재, 개발 디버깅 권한 부재를 검사한다. 프로파일에 해당하는 명시적 앱·팀 식별자가 실제 서명 entitlement에도 포함되어야 한다. 제한된 entitlement는 프로파일 allowlist와 일치해야 하며 Apple의 접두사 wildcard를 허용한다.

macOS sandbox, Hardened Runtime 및 Team prefix App Group은 TN3125에서 설명하는 제한 없는 entitlement이므로 프로파일 allowlist에 없어도 된다. 프로파일을 포함한 패키지에는 양쪽 `embedded.provisionprofile`이 실제 payload 파일 목록에 나타나야 한다. `build/appstore/*.json`에는 각 프로파일의 UUID, 배포 유형, 팀, App ID, 만료 시각과 공개 서명 인증서 지문을 기록하며 프로파일 원문을 저장하지 않는다.

프로파일 검증은 로컬 배포 후보의 서명·프로비저닝 일치 확인이다. App Store Connect validation·업로드, TestFlight 처리·배포 승인 및 테스트 사용자의 설치·실행은 별도의 단계이다. 프로파일을 포함하지 않은 패키지도 기존 일반 Mac App Store 로컬 패키징 동작을 유지하며 JSON의 `testflight_provisioning` 값은 `not_present`가 된다.

Finder Sync 확장에는 `LSUIElement=true`가 필요하며 패키지 도구도 해당 값이 실제 Info.plist에 포함되어 있는지 검사한다. 관련 회귀 테스트는 `python3 -B tests/test_appstore_package.py`로 실행한다. 테스트는 mock 프로파일 메타데이터와 CMS 결과를 사용하며 실제 계정, 개인 키 또는 `.app` fixture를 생성하지 않는다.

## 2026-10-09 온라인 검증 결과

수정 전 pkg는 13:30 KST에 Transporter Verify 오류 `90889`(TestFlight용 호스트 프로파일 누락)와 `90360`(Finder Sync 확장 `LSUIElement` 누락)으로 실패하였다. 양쪽 배포 프로파일과 boolean `LSUIElement=true`를 포함하여 다시 빌드·서명한 당시 `dist/Alright-0.6.1-7-macOS-AppStore.pkg`는 **13:40 KST에 온라인 Verify를 통과하였다**. 완료 화면의 결과는 `VERIFIED ON OCT 9, 2026 AT 13:40`, `Alright - New File in Finder`, `0.6.1 (7)`, Apple ID `6820835356`이다. 이 성공 결과가 적용되는 pkg의 SHA-256은 `12072e88755d716e0959e93277d41fbd242626a03baa5b3eb9247b79a1a5a2ae`이다.

완료 증거는 [Transporter 화면 캡처](../build/verification/build-7-history/Alright-0.6.1-7-macOS-AppStore.verified.png)와 [구조화된 온라인 검증 기록 JSON](../build/verification/build-7-history/Alright-0.6.1-7-macOS-AppStore.appstoreconnect.json)이다. 빌드 `7` 파일은 `build/verification/build-7-history/`에 보관하여 `dist/`의 빌드 `8` 제출 후보와 구분한다. 화면의 완료 시각은 분 단위로만 확인되므로 JSON에서도 실제 관측 시각과 분 단위 완료 표시를 구분한다. macOS TCC 제한으로 Transporter 원본 검증 로그는 확보하지 못하였다. 확보하지 않은 원본 로그가 검증 증거에 포함된 것처럼 서술하지 않는다.

이 결과는 위 해시의 pkg에 대한 온라인 사전 검증 통과이다. 이후 사용자의 아이콘 변경을 반영하여 생성된 pkg는 SHA-256 `9186dafcd0dbd08a4087717788e857e971b34475ba79f985f755a8efd0145949`, 크기 1,298,922바이트로, 앞의 Verify 통과 파일과 다르다. 사용자는 이 파일의 provisioning profile에 포함된 `com.apple.quarantine` 확장 속성에 관한 오류 `91109`를 전달하였다. [Transporter 처리 실패 화면](../build/verification/transporter-91109-processing-failed.png)에서 `DELIVERED ON OCT 9, 2026 AT 14:57`와 `THE APP FAILED PROCESSING WITH 1 ERROR`를 직접 확인하였다. 따라서 `9186dafcd0dbd08a4087717788e857e971b34475ba79f985f755a8efd0145949` 파일은 **전송 완료 후 Apple 서버 처리 실패** 상태이다. 전송 완료·처리 실패는 화면 증거이며 `91109`의 상세 내용은 사용자 제공 오류 메시지에 따른 기록이다. pkg payload의 메모리 검사에서도 양쪽 프로파일의 AppleDouble 메타데이터에 `com.apple.quarantine`이 실제 포함된 것을 확인하였다. TestFlight 빌드 처리·배포 승인, 테스트 사용자의 설치·실행 및 App Review·출시는 완료되지 않았다.

패키지 도구는 `productbuild` 전에 canonical 앱 디렉터리와 내부 전체에서 `com.apple.quarantine`만 제거하고, 양쪽 `embedded.provisionprofile`을 포함한 전체 대상에 해당 속성이 없는지 검증한다. 생성된 pkg의 압축 payload와 AppleDouble ATTR 메타데이터를 메모리에서 검사하여 해당 속성 부재도 확인한다. 다른 확장 속성 이름과 `build/signing/`의 다운로드 원본을 보존하며, 제거 후 앱·확장의 엄격한 코드 서명을 확인한다. 현재 수정본의 로컬 결과는 아래 빌드 `8` 기록에 있다.

다시 패키징하여 pkg의 SHA-256이 바뀌면 이전 온라인 성공 증거는 새 파일의 결과가 아니다. 새 pkg에 대해 Verify를 재실행하고 화면·JSON 증거를 다시 확보한다. [App Store 배포 문서](AppStoreDistribution.md)의 해시 대조와 상태 기록 규칙을 따른다.

## 이전 빌드 8의 온라인 검증 이력

SHA-256 `5d55d4f43efd239483e405b36310b72e3dfdb58619a49e3ff4e4f9fefc87d7df`의 빌드 `8` pkg는 2026-10-09 15:15 KST에 Verify를 통과하였다. 당시 [완료 화면](../build/verification/pkg-history/20261009T063134Z-5d55d4f43efd/Alright-0.6.1-8-macOS-AppStore.verified.png)에서 `0.6.1 (8)` / Apple ID `6820835356`의 `VERIFIED ON OCT 9, 2026 AT 15:15`를 직접 확인하였다. 해당 해시의 [온라인 검증 기록 JSON](../build/verification/pkg-history/20261009T063134Z-5d55d4f43efd/Alright-0.6.1-8-macOS-AppStore.appstoreconnect.json)은 `passed`이며, 분 단위 완료 표시와 실제 관측 시각을 구분한다. 원본 검증 로그는 미확보(`not_captured`)였다.

이전 pkg·manifest·체크섬·온라인 JSON·화면 캡처는 `build/verification/pkg-history/20261009T063134Z-5d55d4f43efd/`에 보관하였다. 이 성공 결과는 아래의 새 pkg에 적용하지 않는다.

## 현재 로컬 pkg 0.6.1 (8)

수정본은 버전 `0.6.1`을 유지하고 호스트와 Finder Sync 확장 모두 빌드 번호 `8`을 사용한다. 사용자 아이콘 변경을 보존하여 반영하였으며, 전송 이력이 있는 빌드 `7`과 새 제출을 구분한다. 새 빌드·CTest `8/8` 및 PackagingUnit `57/57`을 통과하여 `dist/Alright-0.6.1-8-macOS-AppStore.pkg`를 다시 생성하였다. 새 SHA-256은 `597b8f38f86e8f1d22cd272d04d188008ee54355d1fcd4e6bdcb08173c96b9ce`이며 크기는 1,298,801바이트이다. 생성·로컬 검증 시각은 `2026-10-09T15:34:05.468066+09:00`이다. 앱·확장 및 pkg 서명과 신뢰 가능한 타임스탬프 검증을 통과하였다.

빌드 `8`의 manifest는 입력 앱 검사 30개 중 quarantine 제거 2개와 `verified_absent=true`, pkg payload 61개 및 AppleDouble 30개의 `quarantine_absent=true`를 기록한다. 다운로드 원본 프로파일을 변경하지 않고 canonical 앱에 포함된 사본에서만 격리 속성을 처리하였다.

이번 새 파일은 **Transporter에 추가하기 직전까지의 로컬 산출물**이다. 이번 pkg를 Transporter에 추가하지 않았고 온라인 Verify·Deliver·전송·Apple 서버 처리, TestFlight 처리·배포 승인, 테스트 설치·실행 및 App Review·출시는 수행하지 않았다. manifest의 `app_store_connect_validation`, `app_store_connect_upload`, `installation_test`는 모두 `not_performed`이다. `dist/`에는 새 pkg·manifest·체크섬 세 파일만 둔다.

canonical 앱과 pkg payload의 quarantine 0개 확인은 로컬 원인 제거 검증이며, 새 파일의 온라인 검증이나 Apple 서버에서 `91109`가 해결되었다는 증거가 아니다. 과거 빌드 `7`과 이전 해시의 빌드 `8` 온라인 기록은 각각 별도의 이력이다.
