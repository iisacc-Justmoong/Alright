# Mac App Store 패키지

> 현재 제출(2026-10-15 23:54 UTC): `0.6.1 (9)`, `build/appstore/Alright-0.6.1-9-macOS-AppStore.pkg`. 업로드·서버 처리·App Review 제출 완료, 상태 **Waiting for Review**. 미국 기준 USD 0.99와 기존 판매·출시 설정을 유지한다. 상세 상태는 `build/verification/icon-submission-20261015/status.md`와 `deployment-results.json`을 따른다. 아래 빌드 7·8의 dist/ 기록은 과거 이력이다.

Alright의 App Store 배포 후보는 기존 canonical 앱 `build/bin/Alright.app`에서 직접 만든다. Finder Sync 확장도 같은 앱의 `Contents/PlugIns/AlrightFinderSync.appex`에 포함한다. 앱을 `dist/`, 다른 빌드 경로 또는 패키지 검증용 디렉터리에 복사하지 않는다. 새 패키지와 검증 manifest는 `build/appstore/`에만 생성한다. 기존 `dist/` 파일은 과거 업로드 이력으로 보존한다.

## 빌드와 패키지 생성

저장소 루트에서 App Store 서명 구성을 명시하여 빌드한다. Apple Distribution 인증서와 Mac App Store Installer 인증서는 동일한 Apple Developer 팀에서 발급한 것이어야 하며, 개인 키와 함께 로컬 키체인에 존재해야 한다. `Developer ID Installer`는 Mac App Store 제출용 인증서가 아니다.

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DALRIGHT_APP_STORE=ON \
  -DALRIGHT_SIGNING_IDENTITY='Apple Distribution: MUYEONG YUN (5U49ST9XZH)'
cmake --build build
ctest --test-dir build --output-on-failure
python3 -B tools/PackageAppStore.py build \
  --installer-identity '3rd Party Mac Developer Installer: MUYEONG YUN (5U49ST9XZH)'
```

App Store 빌드 구성에서는 `cmake --build build --target AlrightAppStorePackage`로 번들 빌드·서명과 같은 패키지 도구 호출을 한 번에 실행할 수 있다. Installer 신원은 `ALRIGHT_INSTALLER_IDENTITY` CMake 캐시 값으로 설정한다.

TestFlight에도 사용할 배포 후보는 호스트와 확장 프로파일 경로를 함께 지정한다. 현재 확보한 프로파일은 `build/signing/Alright-Mac-AppStore.provisionprofile`과 `build/signing/Alright-FinderSync-Mac-AppStore.provisionprofile`이며, [프로파일 포함 빌드와 검증 절차](TestFlightProfiles.md)의 명령을 따른다. 이 두 경로를 생략한 일반 Store 구성은 TestFlight용 프로파일을 포함하지 않는다.

`PackageAppStore.py`는 Python 표준 라이브러리와 macOS 기본 `codesign`, `security`, `openssl`, `productbuild`, `pkgutil`을 사용한다. `--installer-identity`는 반드시 명시해야 한다. 빌드 경로는 해당 저장소의 `build/`로 제한한다.

패키지 파일명은 서명된 앱의 Info.plist에서 읽은 버전과 빌드 번호로 결정한다. 현재 수정본은 버전 `0.6.1`을 유지하고 호스트·확장의 빌드 번호를 `8`로 사용한다. 2026-10-09 15:34 KST에 빌드·로컬 검증·패키징을 완료하여 다음 산출물을 새로 생성하였다. 2026-10-09 당시 범위는 **Transporter에 추가하기 직전까지의 로컬 작업**이며 새 pkg의 온라인 검증과 전송은 수행하지 않았다.

- `dist/Alright-0.6.1-8-macOS-AppStore.pkg`
- `dist/Alright-0.6.1-8-macOS-AppStore.sha256`
- `dist/Alright-0.6.1-8-macOS-AppStore.json`

같은 버전·빌드 번호로 다시 실행하면 성공한 검증 결과로 해당 세 파일을 갱신한다. 검증 중에는 `build/packaging/` 아래의 임시 디렉터리에 후보 패키지를 만들며, 검증이 실패한 후보는 `dist/`에 배치하지 않는다. 기존에 검증을 통과한 파일은 새 후보가 검증을 마칠 때까지 보존한다.

재패키징 후에는 현재 pkg의 SHA-256과 온라인 검증 증거가 가리키는 SHA-256을 다시 대조한다. 버전·빌드 번호와 파일명이 같아도 서명 타임스탬프 등으로 pkg 바이트가 달라질 수 있다. 해시가 달라졌다면 온라인 성공으로 표시하기 위해서는 새 pkg에 대한 Transporter Verify와 새 증거가 필요하다. 이번 로컬 작업에서는 이를 실행하지 않는다. 이전 화면 캡처나 JSON이 남아 있어도 이전 해시의 성공 상태를 새 파일로 이관하지 않는다.

## 로컬 검증 범위

패키징 전에는 앱과 확장 각각의 엄격한 코드 서명을 검증한다. 서명 유형은 `Apple Distribution` 또는 `3rd Party Mac Developer Application`이어야 하며, 동일한 실제 leaf 인증서와 Team ID를 사용해야 한다. 앱과 확장의 식별자, 실행 파일명, 버전, 빌드 번호를 검사하고, 메인 앱의 `LSApplicationCategoryType`이 `public.app-category.utilities`인지 확인한다. 양쪽 App Sandbox 활성화, 동일한 Alright App Group, `get-task-allow` 비활성화 여부는 서명된 entitlement에서 확인한다.

Installer 인증서는 `security find-identity -v`에 유효한 인증서와 개인 키로 나타나야 한다. 코드 서명 전용 필터인 `-p codesigning`은 Installer 신원을 제외하므로 사용하지 않는다. 키체인 인증서의 실제 지문과 신원 지문을 대조하고, subject의 CN·OU, 만료 여부, Mac App Store 제출용 marker `1.2.840.113635.100.6.1.8`과 Installer EKU `1.2.840.113635.100.4.9`를 검사한다. Apple이 스토어에서 최종 배포할 때 사용하는 Installer 인증서 유형과 개발자가 제출할 때 사용하는 인증서 유형은 구분한다.

패키지는 다음 형태의 `productbuild` 호출로 생성하며 신뢰 가능한 타임스탬프를 요청한다.

```sh
productbuild --component build/bin/Alright.app /Applications \
  --sign '<Mac App Store Installer identity>' --timestamp '<candidate.pkg>'
```

생성 후에는 `pkgutil --check-signature`로 Apple 발급 서명, 선택한 Installer 신원·실제 leaf 인증서 지문, Apple WWDR 인증서 체인과 신뢰 가능한 타임스탬프를 확인한다. macOS 27의 `pkgutil`은 올바른 Mac Installer Distribution 제출용 인증서도 상태 문구에 `(Development)`로 표시한다. 상태 문구만으로 인증서 유형을 판단하지 않고 앞서 검증한 실제 인증서의 제출용 marker·EKU와 선택한 인증서 지문 일치로 제출용 유형을 보장한다.

`pkgutil --payload-files`로 앱과 Finder Sync 확장의 필수 파일을 확인하고, 다른 앱이나 앱 외부로 나가는 경로를 거부한다. 예외는 `productbuild`가 앱 디렉터리의 확장 속성용 AppleDouble 메타데이터로 생성하는 정확한 루트 파일 `._Alright.app` 하나뿐이다. 실제 생성물에서 AppleDouble magic `0x00051607` 및 버전 `0x00020000`을 확인하였으며, `COPYFILE_DISABLE=1`은 이 메타데이터 생성을 막지 않았다. 앱 내부의 `._` 파일도 같은 메타데이터 표현이다. 임의 루트 파일, 다른 앱의 메타데이터, 유사 이름이나 하위 경로는 허용하지 않는다.

`pkgutil --expand`로 `PackageInfo`와 `Distribution`만 확인하며 압축된 Payload는 풀지 않는다. 설치 대상은 `/Applications/Alright.app`이고 Installer 스크립트는 허용하지 않는다. `--expand-full` 또는 앱 설치를 검증 도구에서 수행하지 않는다.

임시 작업의 `TMPDIR`도 `build/packaging/` 내부로 지정한다. 패키징이 끝날 때 `build/`의 앱이 canonical `Alright.app` 하나뿐인지 다시 확인한다. 검증 메타데이터 JSON에는 SHA-256, 앱 버전·빌드 번호, 팀과 공개 인증서 식별 정보, entitlement와 설치 경로 검증 결과를 저장한다. 키체인 또는 인증서 원문과 개인 키·계정 자격 증명은 로그 및 메타데이터에 저장하지 않는다.

이 도구의 성공은 로컬 서명과 패키지 구조 검증 통과를 뜻한다. App Store Connect 온라인 validation, 업로드, 스토어 심사·승인, 구매 후 설치와 동작 검증은 별도의 단계이며, 도구가 생성하는 JSON에는 처음에 `not_performed`로 기록한다. 이후 실제 온라인 결과를 확인한 경우에만 별도의 증거와 함께 해당 상태를 갱신한다. 코드 서명이나 Installer 인증서가 없으면 이 작업은 완료되지 않으며 다른 서명 유형으로 자동 대체하지 않는다.

## App Store Connect 앱 레코드와 Transporter 검증

Apple Developer의 Certificates, Identifiers & Profiles에 Bundle ID를 등록하는 작업과 App Store Connect의 Apps에서 앱 레코드를 생성하는 작업은 별개이다. [Identifier 등록](https://developer.apple.com/help/account/identifiers/register-an-app-id/)은 앱 식별자와 capability 설정을 관리하며, App Store Connect 앱 레코드는 해당 식별자의 빌드와 스토어 정보를 연결한다. Identifier와 서명 인증서가 존재해도 앱 레코드가 자동으로 생성되지는 않는다. [Apple의 앱 레코드 생성 문서](https://developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app)는 빌드 업로드 전에 App Store Connect 앱 레코드를 생성하도록 명시한다.

Transporter가 pkg를 추가하면서 다음 오류를 표시하면, pkg를 재빌드하기 전에 App Store Connect 레코드와 접근 계정을 확인한다.

```text
No suitable application records were found
```

2026-10-09 최초 확인 시 App Store Connect에는 `Time Scopes`와 `iisacc Vincent` 앱 레코드만 있었고, Alright 레코드는 없었다. Apple Developer의 explicit Identifier `com.iisacc.Alright`도 등록되지 않은 상태였다. App Store Connect의 계정과 패키지의 서명 팀은 동일한 `MUYEONG YUN` / `5U49ST9XZH`였다. 이후 해당 explicit Identifier 등록과 아래 App Store Connect 앱 레코드 생성을 완료하였다.

App Store Connect에서 `Alright` 단독 이름은 이미 사용 중이라는 이유로 거부되었다. 최종 스토어 이름은 `Alright - New File in Finder`이며, [생성된 앱 정보 페이지](https://appstoreconnect.apple.com/apps/6820835356/distribution/info)에서 확인한 값은 다음과 같다.

| 항목 | 생성 완료 값 |
| --- | --- |
| 플랫폼 | macOS |
| 스토어 앱 이름 | Alright - New File in Finder |
| 기본 언어 | English (U.S.) |
| Bundle ID | `com.iisacc.Alright` |
| 내부 SKU | `alright-macos` |
| Apple ID | `6820835356` |
| 서명 팀 | `5U49ST9XZH` |
| 앱 접근 설정 | Limited Access; 소유자의 기존 Admin 접근 유지 |

당시 기존 `dist/Alright-0.6.1-7-macOS-AppStore.pkg`를 Transporter에 다시 추가한 결과, Transporter가 앱을 `0.6.1 (7)` / Apple ID `6820835356`으로 인식하였다. 당시 pkg의 SHA-256은 `28876cb092b4a399693a947b0adfaad3b9352c8205111ba4831d29999963dcfc`이며, Identifier와 앱 레코드 생성 과정에서 pkg를 재빌드하거나 재서명하지 않았다. 따라서 최초의 `No suitable application records were found` 오류는 해소되었다.

사용자가 직접 기존 pkg의 Verify를 실행한 뒤 `VERIFYING APP - Analyzing package...` 상태를 관측하였고, 2026-10-09 13:30 KST에 `VERIFICATION FAILED` / `2 ISSUES…`로 종료되었다. 확인된 문제는 `90889`의 TestFlight용 호스트 provisioning profile 누락과 `90360`의 Finder Sync 확장 `LSUIElement` 누락이다. 이 실패는 수정 전 pkg의 검증 이력이다.

호스트·확장에 배포 프로파일을 포함하고 Finder Sync 확장에 boolean `LSUIElement=true`를 추가한 당시 pkg는 **Transporter 온라인 Verify를 통과하였다**. 2026-10-09 13:40 KST 완료 화면에서 `VERIFIED ON OCT 9, 2026 AT 13:40`, 스토어 이름 `Alright - New File in Finder`, 버전 `0.6.1 (7)`, Apple ID `6820835356`을 직접 확인하였다. 이 Verify 통과 대상은 `dist/Alright-0.6.1-7-macOS-AppStore.pkg` 경로의 SHA-256 `12072e88755d716e0959e93277d41fbd242626a03baa5b3eb9247b79a1a5a2ae` 파일이다. 같은 이름으로 새 pkg를 생성해도 이 성공 결과를 새 파일에 자동 적용하지 않는다.

당시 확보한 Verify 완료 증거는 [Transporter 화면 캡처](../build/verification/build-7-history/Alright-0.6.1-7-macOS-AppStore.verified.png)와 [구조화된 온라인 검증 기록 JSON](../build/verification/build-7-history/Alright-0.6.1-7-macOS-AppStore.appstoreconnect.json)이다. JSON은 실제 관측 시각과 화면에 표시된 완료 시각을 구분하며, 완료 표시는 `2026-10-09 13:40 Asia/Seoul`의 분 단위 정밀도로 기록한다. macOS TCC 제한으로 Transporter 원본 검증 로그는 확보하지 못했으므로 원본 로그를 확보한 것처럼 기록하지 않는다. 빌드 `7`의 파일은 `build/verification/build-7-history/`에 이력으로 보관하며, `dist/`의 현재 제출 후보와 구분한다.

이후 사용자가 변경한 아이콘을 반영한 별도 pkg가 생성되었다. 이 파일의 SHA-256은 `9186dafcd0dbd08a4087717788e857e971b34475ba79f985f755a8efd0145949`이며 크기는 1,298,922바이트이다. 버전·빌드 번호가 같아도 앞의 13:40 Verify 통과 파일과 다른 파일이므로 이전 Verify 성공을 이 파일에 적용하지 않는다.

사용자는 이 파일에 대한 오류 `91109`를 전달하였으며, 오류 내용은 번들에 포함된 provisioning profile의 `com.apple.quarantine` 확장 속성이었다. [Transporter 처리 실패 화면](../build/verification/transporter-91109-processing-failed.png)에서는 `0.6.1 (7)` / Apple ID `6820835356`의 `DELIVERED ON OCT 9, 2026 AT 14:57`와 `THE APP FAILED PROCESSING WITH 1 ERROR`를 직접 확인하였다. 따라서 SHA-256 `9186dafcd0dbd08a4087717788e857e971b34475ba79f985f755a8efd0145949` pkg는 **Transporter 전송을 완료한 뒤 Apple 서버 처리에 실패**한 상태이다. 전송 완료와 서버 처리 실패는 화면 증거이며, 오류 번호·상세 내용은 사용자가 제공한 메시지에 따른 기록이다. 해당 pkg의 payload를 메모리에서 검사한 결과 양쪽 프로파일의 AppleDouble 메타데이터에 실제 `com.apple.quarantine`이 포함된 것도 확인하였다. TestFlight 처리·배포 승인, 테스트 설치·실행 및 App Review·출시는 완료되지 않았다. 현재 수정본의 상태는 아래 빌드 `8` 기록과 구분하여 확인한다.

오류 해결과 온라인 검증은 다음 순서로 진행한다.

1. App Store Connect의 Apps 목록에서 `com.iisacc.Alright`를 사용하는 macOS 앱 레코드를 확인한다. 없는 경우 Apps의 추가 버튼에서 New App을 선택하여 생성한다. Bundle ID 선택 목록에 식별자가 없다면 같은 Apple Developer 팀의 Identifiers에서 `com.iisacc.Alright` 등록 상태를 먼저 확인한다.
2. 레코드 생성 후 Apps 목록과 앱 정보 페이지에서 플랫폼, Bundle ID 및 Apple ID를 확인한다. 생성 버튼을 누르거나 입력값을 채운 상태만으로 완료를 기록하지 않는다. 계정에 앱 접근 제한이 있다면 Transporter에서 사용하는 계정이 해당 앱에 접근할 수 있어야 한다. 앱 레코드 생성에는 Account Holder, App Manager 또는 Admin 권한이 필요하며, 최신 약관 미서명도 생성을 막을 수 있다.
3. Transporter의 로그인 계정과 제공자 메뉴가 이 앱 레코드를 가진 계정·제공자를 가리키는지 확인한다. 앱 레코드와 pkg의 Bundle ID가 일치한다면 해당 pkg를 다시 추가한다. 현재 수정본의 경로는 `dist/Alright-0.6.1-8-macOS-AppStore.pkg`이다. 앱 레코드 부재만을 해결하기 위해 소스, Bundle ID, 빌드 번호 또는 서명을 바꾸지는 않는다.
4. Transporter의 옵션 메뉴에서 Verify를 실행하고 완료 결과를 확인한다. Verification Log를 확보할 수 있으면 함께 보존하고, 완료 화면을 증거로 사용하는 경우에는 실제 확보한 증거 종류와 원본 로그 부재를 명시한다. Verify는 App Store Connect 레코드 존재와 패키지 메타데이터·자산 규격을 검사한다. 레코드 생성 성공과 Verify 시작은 온라인 검증 통과와 구분한다. [Apple의 Verify 절차](https://support.apple.com/en-nz/guide/transporter-app/apda53a2df24/mac)와 [계정·제공자 메뉴 설명](https://support.apple.com/en-gb/guide/transporter-app/apdaa2452952/mac)을 따른다.
5. 업로드를 진행하는 경우 Deliver의 성공 결과를 확인한 뒤, App Store Connect에서 해당 빌드의 서버 처리 상태를 확인한다. 현재 수정본은 `0.6.1 (8)`로 확인해야 하며, 과거 빌드 `7`의 상태와 구분한다. Transporter의 전송 완료 이후에도 추가 검증과 처리가 이루어지므로, 전송 완료를 심사 승인이나 출시 완료로 기록하지 않는다. [Apple의 빌드 업로드 절차](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds/)를 따른다.

`PackageAppStore.py`는 온라인 결과를 조회하지 않는다. 별도로 온라인 검증 결과를 배포 manifest에 기록할 때에는 동일한 SHA-256의 pkg에 대한 Transporter Verify 성공 결과를 완료 화면 또는 검증 로그처럼 명시한 증거로 확인한 경우에만 `app_store_connect_validation`을 성공 상태로 기록한다. 앱 레코드 생성, pkg 추가, Verify 시작 또는 로컬 서명 검증만으로 이 필드를 성공 상태로 변경하지 않는다. `app_store_connect_upload` 역시 실제 Deliver 성공 증거가 있어야 하며, 서버 처리·심사·스토어 설치 검증의 완료 여부와 각각 구분한다. 위의 이전 pkg Verify 성공, Transporter 전송 완료, Apple 서버 처리 실패는 각각 이력으로 보존한다. Deliver 완료를 서버 처리 성공으로 기록하지 않는다. 재패키징한 현재 파일의 해시가 달라졌다면 온라인 상태를 미검증으로 시작하고 새 검증 결과를 기록한다.

## 서버 처리 오류 91109와 격리 속성

`91109`로 보고된 provisioning profile 격리 속성이 새 pkg에 포함되지 않도록, `productbuild` 전에 canonical `build/bin/Alright.app` 전체를 확인한다. 앱 디렉터리와 내부의 모든 디렉터리·파일·심볼릭 링크, Finder Sync 확장 및 양쪽 `embedded.provisionprofile`에서 **`com.apple.quarantine` 확장 속성만 제거**한다. `xattr -s`로 각 대상의 속성 이름을 조회하고 해당 속성만 `-d -s`로 제거하므로 심볼릭 링크도 링크 자체를 처리한다. 다른 속성 이름의 보존과 quarantine 부재를 다시 검사하며, `build/signing/`의 다운로드 원본은 변경하지 않는다.

제거 후 동일한 canonical 앱 전체에 `com.apple.quarantine`이 남아 있지 않은지 다시 검증하고, 앱·확장 각각의 엄격한 코드 서명도 확인한 뒤 pkg를 생성한다. 생성한 pkg의 payload와 AppleDouble 메타데이터에도 `com.apple.quarantine`이 없는지 확인한다. 입력 앱의 격리 속성 부재만으로 패키지 내부 속성 부재를 추정하지 않는다. 제거 또는 부재 검증이 실패하면 패키지 생성 완료로 기록하지 않는다. 이 처리를 수행한 새 pkg는 새 SHA-256과 로컬 검증 결과를 기록한다. 이후 온라인 검증·업로드를 수행하는 범위에서는 Transporter Verify, Deliver 및 Apple 서버 처리를 각각 확인한다. 이번 작업은 그 단계 직전에 종료한다. 이전 파일의 Verify 성공 화면을 새 파일의 온라인 성공 증거로 표시하지 않는다.

Payload 검사는 gzip 및 odc CPIO를 메모리에서 읽고 AppleDouble의 ATTR 속성 이름 구조를 해석하여 quarantine을 찾는다. 격리 속성이 발견되면 후보 pkg를 거부한다. 압축을 풀어 `.app` 복사본을 만들거나 확장 속성 값의 원문을 로그에 기록하지 않는다. manifest의 `quarantine_sanitization`은 canonical 입력 앱의 검사·제거 결과이고, `payload_quarantine_validation`은 생성된 pkg 내부 검사 결과이다.

## 이전 빌드 8의 온라인 검증 이력

2026-10-09 15:15 KST에 Verify를 통과한 빌드 `8` 파일의 SHA-256은 `5d55d4f43efd239483e405b36310b72e3dfdb58619a49e3ff4e4f9fefc87d7df`이며 크기는 1,298,773바이트이다. 당시 [완료 화면](../build/verification/pkg-history/20261009T063134Z-5d55d4f43efd/Alright-0.6.1-8-macOS-AppStore.verified.png)에서 `0.6.1 (8)` / Apple ID `6820835356`의 `VERIFIED ON OCT 9, 2026 AT 15:15`를 직접 확인하였다. 해당 해시에 연결된 [온라인 검증 기록 JSON](../build/verification/pkg-history/20261009T063134Z-5d55d4f43efd/Alright-0.6.1-8-macOS-AppStore.appstoreconnect.json)은 `passed`이다. 완료 시각의 분 단위 표시와 실제 관측 시각을 구분하여 기록했고 원본 검증 로그는 미확보(`not_captured`)였다.

이전 파일과 JSON·체크섬·화면 캡처는 `build/verification/pkg-history/20261009T063134Z-5d55d4f43efd/`에 이력으로 보관하였다. 이 Verify 성공은 아래의 새 해시에 적용되지 않는다.

## 2026-10-09 로컬 pkg 0.6.1 (8)

현재 수정본은 `0.6.1 (8)`이다. 이미 Transporter 전송 이력이 있는 빌드 `7`과 구분하기 위해 호스트·Finder Sync 확장의 빌드 번호를 함께 `8`로 변경하였다. 사용자가 추가한 최신 아이콘 변경을 보존하여 이 빌드에 반영하였다. 생성 아이콘과 canonical 아이콘의 SHA-256은 모두 `4b83157560188b82a2cec25121c7afdc689faa61afeb976b543117645431764f`이다.

새 빌드와 CTest `8/8`을 통과했으며 PackagingUnit은 `57/57`을 통과하였다. 새 `dist/Alright-0.6.1-8-macOS-AppStore.pkg`의 SHA-256은 `597b8f38f86e8f1d22cd272d04d188008ee54355d1fcd4e6bdcb08173c96b9ce`이며 크기는 1,298,801바이트이다. 생성·로컬 검증 시각은 `2026-10-09T15:34:05.468066+09:00`이며, manifest의 `verified_at_utc`는 같은 시각을 UTC로 기록한다. 앱·확장 코드 서명, pkg 서명과 신뢰 가능한 타임스탬프 검증을 통과하였다. 이 파일의 manifest에서 확인한 quarantine 검증은 다음과 같다.

| 검증 필드 | 결과 |
| --- | --- |
| `quarantine_sanitization.removed_count` | 2 |
| `quarantine_sanitization.inspected_count` | 30 |
| `quarantine_sanitization.verified_absent` | `true` |
| `payload_quarantine_validation.payload_entries` | 61 |
| `payload_quarantine_validation.appledouble_count` | 30 |
| `payload_quarantine_validation.quarantine_absent` | `true` |

새 해시 파일의 완료 범위는 **로컬 빌드·테스트·서명 pkg 생성과 canonical 앱·pkg payload의 quarantine 부재 검증**이다. 2026-10-09 당시 새 pkg는 Transporter에 추가하지 않았으며 온라인 Verify·Deliver·전송·Apple 서버 처리, TestFlight 처리·배포 승인, 테스트 설치·실행 및 App Review·출시를 수행하지 않았다. 당시 manifest의 `app_store_connect_validation`, `app_store_connect_upload`, `installation_test`는 모두 `not_performed`이었다. `dist/`에는 현재 pkg·manifest JSON·체크섬 세 파일만 두며, 과거 온라인 성공 증거를 현재 파일 옆에 표시하지 않는다.

입력 앱과 생성 payload의 quarantine은 각각 0개로 확인하였다. 이 결과는 로컬 원인 제거 검증이며 새 파일의 온라인 사전 검증이나 Apple 서버의 `91109` 해결 완료를 뜻하지 않는다. 빌드 `7`과 이전 해시의 빌드 `8` 온라인 결과는 각각 보관 경로의 이력으로 유지한다.

## Finder Sync 확장의 LSUIElement

Transporter의 `90360` 검증 오류를 방지하려면 `AlrightFinderSync.appex/Contents/Info.plist`에 `LSUIElement`를 boolean `true`로 선언한다. `resources/FinderSync-Info.plist.in`은 `<key>LSUIElement</key><true/>`를 사용한다. 문자열 `"true"`나 숫자 `1`로 대체하지 않는다. [Apple의 LSUIElement 문서](https://developer.apple.com/documentation/bundleresources/information-property-list/lsuielement)는 이 키의 타입을 boolean으로 정의하며, Dock에 표시되지 않는 agent 앱 동작을 지정한다.

`tests/test_bundle.py`는 실제 canonical 앱 안의 Finder Sync 확장 plist를 읽어 `LSUIElement`가 boolean `True`인지 회귀 검증한다. 이 선언을 추가한 뒤에는 앱·확장을 다시 빌드하고 서명한 pkg로 Transporter Verify를 재실행해야 한다. 소스 수정이나 로컬 검증 통과만으로 `90360`의 온라인 해결 완료를 기록하지 않는다.

## 검증 도구 테스트

```sh
python3 -B tests/test_appstore_package.py
```

테스트는 배포 구성의 잘못된 버전, 식별자, sandbox, App Group, 개발용 entitlement, 팀·인증서 유형·지문 불일치, 키체인 신원 부재, 타임스탬프 부재, 잘못된 payload 및 설치 경로를 검사한다. 메타데이터와 외부 명령을 mock으로 검증하여 추가 `.app`이나 서명용 fixture를 생성하지 않는다.

Apple의 패키징 절차는 [Packaging Mac software for distribution](https://developer.apple.com/documentation/xcode/packaging-mac-software-for-distribution)을 따른다. 인증서 CN·OU 및 App Store 제출용 서명 유형은 [TN3161: Inside Code Signing: Certificates](https://developer.apple.com/documentation/technotes/tn3161-inside-code-signing-certificates)를 참고한다. Installer marker와 EKU의 분류는 [Apple Security의 SecPolicy.c](https://github.com/apple-oss-distributions/Security/blob/main/OSX/sec/Security/SecPolicy.c)의 MacDistributionInstaller와 ExternalDeveloper 정책에서 확인할 수 있다.


## 2026-10-10 재검증 및 재업로드

현재 `dist/Alright-0.6.1-8-macOS-AppStore.pkg`를 다시 검증하고 기존 Transporter 로그인으로 재업로드하였다. SHA-256은 `597b8f38f86e8f1d22cd272d04d188008ee54355d1fcd4e6bdcb08173c96b9ce`로 유지되었고, Apple ID는 `6820835356`이다. 기존 작업 트리에 이미 포함된 `PackageAppStore.py`의 quarantine 정리·payload 검사와 회귀 테스트를 보존하여 재사용하였다. 이번 실행에서는 소스 수정, 새 배포 앱 생성·재서명, 실제 quarantine 속성 제거를 수행하지 않았다.

`AlrightTests`, `AlrightDocumentFixture`, `AlrightIconGenerator` 타깃 빌드가 성공했고 CTest는 `8/8`, PackagingUnit은 `57/57`을 통과했다. 배포 앱과 pkg는 기존 검증 후보를 재사용했다. 일반 macOS 실행 환경에서 앱·확장의 엄격한 배포 서명, entitlement, 동일한 인증서·팀 및 양쪽 Mac App Store 프로파일을 다시 검증했다. canonical 앱 30개 항목의 quarantine은 0개였고 다운로드 원본 프로파일의 속성은 변경하지 않았다. 완성 pkg의 Installer 서명·신뢰 타임스탬프·설치 경로·구조 검증도 통과했다. 압축 payload 61개 항목과 AppleDouble 메타데이터 30개에서 quarantine 부재를 확인했으며, 실제 파일 19개의 바이트가 canonical 앱과 일치했다. 추가 `.app` 복사본을 만들지 않았다.

현재 파일을 Transporter에 다시 추가해 이전 Verify 캐시를 교체한 후 새 Verify를 실행했다. `VERIFIED ON OCT 10, 2026 AT 19:15`를 확인했고, 이어 `DELIVERED ON OCT 10, 2026 AT 19:17`를 확인했다. 화면 표시 시각은 Asia/Seoul의 분 단위이며 각각 `2026-10-10 10:15 UTC`, `10:17 UTC`이다. [현재 해시의 Verify 완료 화면](../build/verification/reupload-20261010/transporter-verified.png), [Deliver 완료 화면](../build/verification/reupload-20261010/transporter-delivered.png), [온라인 결과 JSON](../build/verification/reupload-20261010/deployment-results.json), [로컬 패키지 검증 JSON](../build/verification/reupload-20261010/local-validation.json)과 [실행 결과 보고서](../build/verification/reupload-20261010/status.md)를 보존하였다. 원본 Transporter 검증·전송 로그는 파일 경로에서 확보하지 못했고 성공 화면을 증거로 사용한다.

10:29 UTC 조회 시점에는 Apple 서버 처리 성공을 확인하지 못했다. 당시 App Store Connect 브라우저는 재로그인이 필요했으며, Transporter의 전송 완료를 서버 처리 완료·TestFlight 승인·App Review 승인으로 기록하지 않는다. `dist/`의 manifest는 실제 같은 해시의 새 Verify·Deliver 성공 증거를 연결하고 서버 처리를 `not_confirmed`로 기록한다. 공개 릴리스, 가격·메타데이터 변경, 새 약관 수락 또는 OS 보안 설정·권한 변경은 수행하지 않았다.

10:29 UTC의 이전 후속 조회에서도 App Store Connect는 로그인 화면이었고 2026-10-10의 Alright 관련 Apple 메일은 발견되지 않았다. 재업로드 후 추가 Transporter 스크린샷은 확보하지 못했으므로 10:17 UTC Deliver 완료 증거만 근거로 사용한다. 서버 처리 결과는 기존 Apple 계정으로 App Store Connect에 재로그인한 뒤 build 8에서 확인해야 한다. 보안 설정 변경이나 quarantine 제거 승인 대기는 없다.

## 2026-10-10 기존 로그인 복구와 Apple 서버 처리 완료 확인

Safari에 이미 저장된 해당 Apple 계정의 로그인을 일반 로그인 UI에서 적용해 App Store Connect 세션을 복구하였다. 사용자 암호 입력이나 추가 인증은 필요하지 않았다. 새 자격증명 생성, OS 보안 설정·권한 변경 및 새 약관 수락은 수행하지 않았다.

인증된 [macOS 빌드 페이지](https://appstoreconnect.apple.com/apps/6820835356/testflight/macos)의 `Build Uploads` 표에서 `0.6.1 (8)`은 **`Complete`**, 과거 `0.6.1 (7)`은 `Failed`로 확인하였다. [처리 완료 확인 화면](../build/verification/reupload-20261010/appstoreconnect-build-8-complete.png)과 [온라인 결과 JSON](../build/verification/reupload-20261010/deployment-results.json)을 저장하였다. 화면 캡처 관측 시각은 `2026-10-10T10:40:25.011269+00:00`이며, 실제 서버 처리 완료 시각은 화면에 표시되지 않는다. 이전 10:29 UTC의 `not_confirmed` 기록은 이력으로 보존하고 현재 manifest의 `app_store_connect_processing`을 `complete`로 갱신하였다.

별도 TestFlight 표에서 build `8`은 **`Missing Compliance`**로 표시된다. 이 값의 변경, 관련 신고 제출, 테스터 배포, App Review 승인 및 공개 릴리스를 수행하지 않았다. 이번 후속 확인에서는 새 업로드를 실행하지 않았으며, 기존 패키지의 SHA-256 `597b8f38f86e8f1d22cd272d04d188008ee54355d1fcd4e6bdcb08173c96b9ce` 및 빌드·테스트·로컬 검증 결과는 그대로 유지하였다. 인증된 Safari 페이지는 열어 두었다.

## 2026-10-15 새 아이콘 제출 후보

사용자가 지정한 Workspace `build/app-icon-20261015/Glossy-Blue-File-Add`의 AI·SVG·PNG를 `resources/AppIcon/Alright.*`에 바이트 변경 없이 적용하였다. PNG의 실제 픽셀과 기존 Alright 아이콘을 대조하고, 프로젝트 배포 문서와 인증된 ASC 앱 정보의 macOS / `com.iisacc.Alright` / Apple ID `6820835356`을 확인하여 대상을 식별하였다. 기존 소스 변경은 보존하며 교체 전 파일과 diff를 `build/verification/icon-submission-20261015/`에 보관한다.

현재 프로젝트 버전 `0.6.1`을 유지하고 호스트·확장의 빌드 번호는 기존 ASC 최대 빌드 `8` 다음인 `9`로 올린다. 패키지 도구의 신규 출력 위치는 `build/appstore/Alright-0.6.1-9-macOS-AppStore.pkg`이며 `.sha256`과 `.json`을 함께 만든다. 위의 `dist/` 경로·해시는 이전 실행의 이력이다. 신규 파일의 온라인 검증·전송·처리·심사 제출은 실제 완료 증거를 얻은 뒤 별도로 기록한다.

ASC 사전 확인에서 미국 기준 가격은 이미 USD 0.99이며, 175개 국가·지역 판매, Apple의 자동 가격 조정, Public 배포, 교육용 대량 구매 할인과 자동 승인 후 출시 설정이 존재한다. 이 설정을 유지한다. 현재 ASC 제출 초안 버전은 `1.0`이고 빌드 미선택 상태이며, 업로드 후보의 버전과 연결할 때 프로젝트의 `0.6.1`에 맞춘다. 기존 스크린샷 두 개와 연령 등급은 보존한다.

새 후보는 Release / macOS 14.0 이상 / arm64로 빌드했으며, 호스트와 확장 모두 Apple Distribution·팀 `5U49ST9XZH`, 기존 두 배포 프로파일과 App Sandbox를 사용한다. CTest 8/8 및 iiFileProvider Swift 6 adapter 실행 검사가 통과하였다. 현재 사용자 작업본의 SDK 연동을 보존했으며, NSLock으로 이미 보호된 `pendingPreviews` 선언 한 곳에 Swift 6의 외부 동기화 표시를 추가하여 빌드 오류를 해결하였다.

로컬 검증을 통과한 pkg의 SHA-256은 `a39c7ac45fed8317d872d219a3f6a6ccdfb27939c55ab9d4aec323149e9eb419`, 크기는 1,358,255바이트이다. 압축 payload를 스트림으로 읽어 ICNS와 양쪽 Info.plist가 canonical 앱과 바이트 단위로 일치함을 추가 확인했다. 새 `.app` 복사본은 만들지 않았다. `build/verification/icon-submission-20261015/`의 `ctest.xml`, `payload-validation.json`, `sdk-build-fix.json` 및 로그가 근거이다.

2026-10-15 23:33 UTC(Transporter 표시: 2026-10-16 08:33 Asia/Seoul)에 빌드 `0.6.1 (9)`의 Deliver가 완료되었다. Transporter의 `THE APP HAS FINISHED PROCESSING.`과 ASC TestFlight의 Build Uploads `Complete`를 각각 확인했다. 소스와 실제 링크 의존성에서 Apple OS 외부의 암호화 구현이 없는 것을 확인한 뒤 ASC 암호화 질문에서 `None of the algorithms mentioned above`를 저장하였으며, 빌드 상태가 `Ready to Submit`로 바뀌었다. 별도의 Verify 명령은 실행하지 않았고 Deliver의 내장 validation을 통과한 전송 결과이다. 심사 제출 성공과 구분한다. 관측 기록은 `transporter-delivery-observation.json`, `asc-build-9-complete.json`에 보존한다.

## 2026-10-15 23:54 UTC App Review 제출 완료

필수 심사 연락처 이름·성은 사용자가 허용한 `Muyeong / Yun`으로 저장했다. 전화·이메일과 함께 페이지 재로드 후 영속화된 값을 확인했으며, 기존 빌드 `0.6.1 (9)`를 재업로드하지 않았다. Add for Review 검증을 통과한 한 항목을 Submit for Review로 제출하여 `1 Item Submitted`, Draft Submissions `0`, 앱 버전과 제출 상세의 **Waiting for Review**를 확인했다. 제출 ID는 `5ccee0ab-5fc0-4750-8246-2d56908d8be6`이고 [접수 상세](https://appstoreconnect.apple.com/apps/6820835356/distribution/reviewsubmissions/details/5ccee0ab-5fc0-4750-8246-2d56908d8be6)의 Date Submitted는 `Oct 16, 2026 at 8:54 AM (Asia/Seoul)`이다. UTC로 `2026-10-15 23:54`이며 ASC 표시 정밀도는 분 단위이다. `build/verification/icon-submission-20261015/app-review-submitted.json` 및 `review-submission-timing.json`에 표시 시각과 확인 시각을 구분해 기록했다. 심사 승인·출시나 구매 후 설치 검증은 아직 완료되지 않았다.
