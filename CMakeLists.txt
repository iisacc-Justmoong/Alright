cmake_minimum_required(VERSION 3.24)
include(cmake/single-app/Defaults.cmake)
set(CMAKE_OSX_DEPLOYMENT_TARGET "14.0" CACHE STRING "Minimum macOS version")
project(Alright VERSION 0.6.1 LANGUAGES Swift)

if(NOT CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    message(FATAL_ERROR "Alright currently requires macOS and AppKit.")
endif()
if(NOT CMAKE_BINARY_DIR STREQUAL "${CMAKE_SOURCE_DIR}/build")
    message(FATAL_ERROR "Use the project build/ directory: cmake -S . -B build")
endif()

set(CMAKE_Swift_LANGUAGE_VERSION 6)
# Swift's Ninja driver otherwise defaults to the build host OS version.
if(CMAKE_OSX_ARCHITECTURES)
    set(ALRIGHT_ARCH "${CMAKE_OSX_ARCHITECTURES}")
else()
    set(ALRIGHT_ARCH "${CMAKE_SYSTEM_PROCESSOR}")
endif()
if(NOT ALRIGHT_ARCH MATCHES "^(arm64|x86_64)$")
    message(FATAL_ERROR "Build one macOS architecture at a time: arm64 or x86_64")
endif()
add_compile_options(-target "${ALRIGHT_ARCH}-apple-macosx${CMAKE_OSX_DEPLOYMENT_TARGET}")
find_library(APPKIT_FRAMEWORK AppKit REQUIRED)
find_library(FINDER_SYNC_FRAMEWORK FinderSync REQUIRED)
set(ALRIGHT_SIGNING_IDENTITY "Developer ID Application: MUYEONG YUN (5U49ST9XZH)" CACHE STRING "Host and extension signing identity")
set(ALRIGHT_TEAM_ID "5U49ST9XZH" CACHE STRING "Signing identity team identifier")
option(ALRIGHT_APP_STORE "Build the sandboxed Mac App Store distribution channel" OFF)
set(ALRIGHT_INSTALLER_IDENTITY "3rd Party Mac Developer Installer: MUYEONG YUN (5U49ST9XZH)" CACHE STRING "Mac App Store installer signing identity")
set(ALRIGHT_HOST_PROVISION_PROFILE "" CACHE FILEPATH "Optional Mac App Store host provisioning profile")
set(ALRIGHT_EXTENSION_PROVISION_PROFILE "" CACHE FILEPATH "Optional Mac App Store Finder Sync provisioning profile")
if(ALRIGHT_HOST_PROVISION_PROFILE OR ALRIGHT_EXTENSION_PROVISION_PROFILE)
    if(NOT ALRIGHT_APP_STORE)
        message(FATAL_ERROR "Provisioning profiles require ALRIGHT_APP_STORE=ON")
    endif()
    if(NOT ALRIGHT_HOST_PROVISION_PROFILE OR NOT ALRIGHT_EXTENSION_PROVISION_PROFILE)
        message(FATAL_ERROR "Set both ALRIGHT_HOST_PROVISION_PROFILE and ALRIGHT_EXTENSION_PROVISION_PROFILE")
    endif()
    foreach(profile IN ITEMS ALRIGHT_HOST_PROVISION_PROFILE ALRIGHT_EXTENSION_PROVISION_PROFILE)
        get_filename_component(${profile} "${${profile}}" ABSOLUTE BASE_DIR "${CMAKE_SOURCE_DIR}")
        if(NOT EXISTS "${${profile}}" OR IS_DIRECTORY "${${profile}}")
            message(FATAL_ERROR "${profile} must name an existing provisioning profile file")
        endif()
    endforeach()
endif()
if(ALRIGHT_APP_STORE)
    if(NOT ALRIGHT_SIGNING_IDENTITY MATCHES "^(Apple Distribution|3rd Party Mac Developer Application):")
        message(FATAL_ERROR "App Store builds require ALRIGHT_SIGNING_IDENTITY to name an Apple Distribution or Mac App Distribution certificate")
    endif()
    set(ALRIGHT_APP_STORE_SWIFT true)
    set(ALRIGHT_APP_SANDBOX_ENTITLEMENT "<key>com.apple.security.app-sandbox</key><true/>")
    set(ALRIGHT_SIGNING_TIMESTAMP --timestamp)
else()
    set(ALRIGHT_APP_STORE_SWIFT false)
    set(ALRIGHT_APP_SANDBOX_ENTITLEMENT "")
    set(ALRIGHT_SIGNING_TIMESTAMP --timestamp=none)
endif()
set(ALRIGHT_APP_GROUP "${ALRIGHT_TEAM_ID}.com.iisacc.Alright")
configure_file(resources/App.entitlements.in App.entitlements @ONLY)
configure_file(resources/FinderSync.entitlements.in FinderSync.entitlements @ONLY)
set(ALRIGHT_PROFILE_COMMANDS
    COMMAND "${CMAKE_COMMAND}" -E rm -f "$<TARGET_BUNDLE_DIR:Alright>/Contents/embedded.provisionprofile"
        "$<TARGET_BUNDLE_DIR:AlrightFinderSync>/Contents/embedded.provisionprofile")
if(ALRIGHT_HOST_PROVISION_PROFILE)
    # TestFlight profiles authorize each executable's explicit application identity.
    foreach(bundle IN ITEMS App FinderSync)
        if(bundle STREQUAL "App")
            set(bundle_identifier "com.iisacc.Alright")
        else()
            set(bundle_identifier "com.iisacc.Alright.FinderSync")
        endif()
        file(READ "${CMAKE_BINARY_DIR}/${bundle}.entitlements" entitlements)
        string(REPLACE "</dict>"
            "<key>com.apple.application-identifier</key><string>${ALRIGHT_TEAM_ID}.${bundle_identifier}</string><key>com.apple.developer.team-identifier</key><string>${ALRIGHT_TEAM_ID}</string></dict>"
            entitlements "${entitlements}")
        file(WRITE "${CMAKE_BINARY_DIR}/${bundle}.entitlements" "${entitlements}")
    endforeach()
    list(APPEND ALRIGHT_PROFILE_COMMANDS
        COMMAND "${CMAKE_COMMAND}" -E copy_if_different "${ALRIGHT_HOST_PROVISION_PROFILE}"
            "$<TARGET_BUNDLE_DIR:Alright>/Contents/embedded.provisionprofile"
        COMMAND "${CMAKE_COMMAND}" -E copy_if_different "${ALRIGHT_EXTENSION_PROVISION_PROFILE}"
            "$<TARGET_BUNDLE_DIR:AlrightFinderSync>/Contents/embedded.provisionprofile")
endif()

configure_file(resources/BuildConfiguration.swift.in generated/BuildConfiguration.swift @ONLY)
find_package(iiFileProviderSwift 0.6 CONFIG REQUIRED)
set(ALRIGHT_SHARED ${iiFileProviderSwift_SOURCE} src/core/DocumentCreator.swift src/core/DocumentKind.swift src/core/CanvasSize.swift src/core/PhotoshopDocument.swift src/core/IllustratorDocument.swift src/shared/FolderStore.swift "${CMAKE_BINARY_DIR}/generated/BuildConfiguration.swift")
set(ALRIGHT_APP src/app/AppDelegate.swift src/app/DocumentService.swift src/app/FinderRenamer.swift src/shared/Symbols.swift)
add_executable(AlrightFinderSync MACOSX_BUNDLE ${ALRIGHT_SHARED} src/finder_extension/FinderSync.swift src/finder_extension/main.swift)
target_link_libraries(AlrightFinderSync PRIVATE "${APPKIT_FRAMEWORK}" "${FINDER_SYNC_FRAMEWORK}")
set_target_properties(AlrightFinderSync PROPERTIES
    BUNDLE_EXTENSION appex
    XCODE_PRODUCT_TYPE "com.apple.product-type.app-extension"
    MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/resources/FinderSync-Info.plist.in"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/build/bin/Alright.app/Contents/PlugIns$<0:>"
    XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED NO
    XCODE_ATTRIBUTE_SKIP_INSTALL YES)

add_executable(AlrightIconGenerator tools/GenerateIcon.swift)
target_compile_options(AlrightIconGenerator PRIVATE -parse-as-library)
target_link_libraries(AlrightIconGenerator PRIVATE "${APPKIT_FRAMEWORK}")
set(ALRIGHT_ICON "${CMAKE_BINARY_DIR}/generated/Alright.icns")
add_custom_command(OUTPUT "${ALRIGHT_ICON}"
    COMMAND AlrightIconGenerator "${CMAKE_SOURCE_DIR}/resources/AppIcon/Alright.png"
        "${CMAKE_BINARY_DIR}/generated/Alright.iconset"
    COMMAND /usr/bin/iconutil -c icns "${CMAKE_BINARY_DIR}/generated/Alright.iconset" -o "${ALRIGHT_ICON}"
    DEPENDS AlrightIconGenerator tools/GenerateIcon.swift resources/AppIcon/Alright.png VERBATIM)
set_source_files_properties("${ALRIGHT_ICON}" PROPERTIES MACOSX_PACKAGE_LOCATION Resources GENERATED TRUE)
add_executable(Alright MACOSX_BUNDLE ${ALRIGHT_SHARED} ${ALRIGHT_APP} src/app/main.swift "${ALRIGHT_ICON}")
target_link_libraries(Alright PRIVATE "${APPKIT_FRAMEWORK}" "${FINDER_SYNC_FRAMEWORK}")
set_target_properties(Alright PROPERTIES
    MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/resources/Info.plist.in"
    XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED NO)
file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/modules")
foreach(target IN ITEMS Alright AlrightFinderSync AlrightIconGenerator)
    target_compile_options(${target} PRIVATE -emit-module-path "${CMAKE_BINARY_DIR}/modules/${target}.swiftmodule" -emit-module-dependencies-path "${CMAKE_BINARY_DIR}/CMakeFiles/${target}.emit-module.d")
endforeach()
find_package(Python3 REQUIRED COMPONENTS Interpreter)
file(GLOB_RECURSE ALRIGHT_OFFICE_SOURCES CONFIGURE_DEPENDS "${CMAKE_SOURCE_DIR}/resources/OfficeTemplates/*")
set(ALRIGHT_OFFICE_OUTPUTS)
foreach(format IN ITEMS docx xlsx pptx odt ods odp)
    list(APPEND ALRIGHT_OFFICE_OUTPUTS "${CMAKE_BINARY_DIR}/generated/OfficeTemplates/Blank.${format}")
endforeach()
add_custom_command(OUTPUT ${ALRIGHT_OFFICE_OUTPUTS}
    COMMAND "${Python3_EXECUTABLE}" -B "${CMAKE_SOURCE_DIR}/tools/BuildOfficeTemplates.py"
        "${CMAKE_SOURCE_DIR}/resources/OfficeTemplates" "${CMAKE_BINARY_DIR}/generated/OfficeTemplates"
    DEPENDS ${ALRIGHT_OFFICE_SOURCES} tools/BuildOfficeTemplates.py VERBATIM)
add_custom_target(AlrightBundle ALL
    COMMAND "${CMAKE_COMMAND}" -E make_directory "$<TARGET_BUNDLE_DIR:Alright>/Contents/Resources"
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different "${ALRIGHT_ICON}" "$<TARGET_BUNDLE_DIR:Alright>/Contents/Resources/Alright.icns"
    COMMAND "${CMAKE_COMMAND}" -E copy_directory "${CMAKE_SOURCE_DIR}/resources/DocumentTemplates" "$<TARGET_BUNDLE_DIR:Alright>/Contents/Resources/DocumentTemplates"
    COMMAND "${CMAKE_COMMAND}" -E copy_directory "${CMAKE_BINARY_DIR}/generated/OfficeTemplates" "$<TARGET_BUNDLE_DIR:Alright>/Contents/Resources/DocumentTemplates"
    COMMAND "${CMAKE_COMMAND}" "-DSOURCE=$<TARGET_FILE:Alright>.dSYM"
        "-DDESTINATION=${CMAKE_BINARY_DIR}/symbols/Alright.dSYM"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/MoveDebugSymbols.cmake"
    COMMAND "${CMAKE_COMMAND}" "-DSOURCE=$<TARGET_FILE:AlrightFinderSync>.dSYM"
        "-DDESTINATION=${CMAKE_BINARY_DIR}/symbols/AlrightFinderSync.dSYM"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/MoveDebugSymbols.cmake"
    COMMAND "${CMAKE_COMMAND}" "-DSOURCE=$<TARGET_FILE:Alright>.d"
        "-DDESTINATION=${CMAKE_BINARY_DIR}/CMakeFiles/Alright.swift-link.d"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/MoveDebugSymbols.cmake"
    COMMAND "${CMAKE_COMMAND}" "-DSOURCE=$<TARGET_FILE:AlrightFinderSync>.d"
        "-DDESTINATION=${CMAKE_BINARY_DIR}/CMakeFiles/AlrightFinderSync.swift-link.d"
        -P "${CMAKE_CURRENT_SOURCE_DIR}/cmake/MoveDebugSymbols.cmake"
    ${ALRIGHT_PROFILE_COMMANDS}
    COMMAND /usr/bin/codesign --force ${ALRIGHT_SIGNING_TIMESTAMP} --options runtime --sign "${ALRIGHT_SIGNING_IDENTITY}"
        --entitlements "${CMAKE_BINARY_DIR}/FinderSync.entitlements" "$<TARGET_BUNDLE_DIR:AlrightFinderSync>"
    COMMAND /usr/bin/codesign --force ${ALRIGHT_SIGNING_TIMESTAMP} --options runtime --sign "${ALRIGHT_SIGNING_IDENTITY}"
        --entitlements "${CMAKE_BINARY_DIR}/App.entitlements" "$<TARGET_BUNDLE_DIR:Alright>"
    DEPENDS Alright AlrightFinderSync "${ALRIGHT_ICON}" ${ALRIGHT_OFFICE_OUTPUTS}
    VERBATIM)
add_custom_target(AlrightRegisterExtension
    COMMAND /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
        -f "$<TARGET_BUNDLE_DIR:Alright>"
    COMMAND /usr/bin/pluginkit -a "$<TARGET_BUNDLE_DIR:AlrightFinderSync>"
    DEPENDS AlrightBundle VERBATIM)
if(ALRIGHT_APP_STORE)
    add_custom_target(AlrightAppStorePackage
        COMMAND "${Python3_EXECUTABLE}" -B "${CMAKE_SOURCE_DIR}/tools/PackageAppStore.py"
            "${CMAKE_BINARY_DIR}" --installer-identity "${ALRIGHT_INSTALLER_IDENTITY}"
        DEPENDS AlrightBundle VERBATIM)
endif()

include(CTest)
if(BUILD_TESTING)
    add_executable(AlrightTests ${ALRIGHT_SHARED} ${ALRIGHT_APP} src/finder_extension/FinderSync.swift tests/Tests.swift)
    target_compile_options(AlrightTests PRIVATE -parse-as-library -emit-module-path "${CMAKE_BINARY_DIR}/modules/AlrightTests.swiftmodule" -emit-module-dependencies-path "${CMAKE_BINARY_DIR}/CMakeFiles/AlrightTests.emit-module.d")
    target_link_libraries(AlrightTests PRIVATE "${APPKIT_FRAMEWORK}" "${FINDER_SYNC_FRAMEWORK}")
    foreach(suite IN ITEMS NewText Documents Requests FinderMenu AppLifecycle)
        add_test(NAME Alright.${suite} COMMAND AlrightTests ${suite} "${CMAKE_BINARY_DIR}/fixtures/swift-tests" "${CMAKE_BINARY_DIR}/bin/Alright.app/Contents/Resources/DocumentTemplates")
    endforeach()
    add_executable(AlrightDocumentFixture ${ALRIGHT_SHARED} tools/GenerateDocumentFixture.swift)
    target_compile_options(AlrightDocumentFixture PRIVATE -parse-as-library -emit-module-path "${CMAKE_BINARY_DIR}/modules/AlrightDocumentFixture.swiftmodule" -emit-module-dependencies-path "${CMAKE_BINARY_DIR}/CMakeFiles/AlrightDocumentFixture.emit-module.d")
    target_link_libraries(AlrightDocumentFixture PRIVATE "${APPKIT_FRAMEWORK}")
    add_test(NAME Alright.OfficePackages COMMAND "${Python3_EXECUTABLE}" -B
        "${CMAKE_SOURCE_DIR}/tests/test_office_packages.py" "${CMAKE_BINARY_DIR}")
    add_test(NAME Alright.Bundle COMMAND "${Python3_EXECUTABLE}" -B
        "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_bundle.py" "${CMAKE_BINARY_DIR}")
    add_test(NAME Alright.AppStorePackaging COMMAND "${Python3_EXECUTABLE}" -B
        "${CMAKE_CURRENT_SOURCE_DIR}/tests/test_appstore_package.py")
endif()

include(cmake/single-app/SingleApp.cmake)
cmake_language(DEFER CALL product_single_app Alright "bin")
