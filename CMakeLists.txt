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
set(ALRIGHT_APP_GROUP "${ALRIGHT_TEAM_ID}.com.iisacc.Alright")
configure_file(resources/App.entitlements.in App.entitlements @ONLY)
configure_file(resources/FinderSync.entitlements.in FinderSync.entitlements @ONLY)

configure_file(resources/BuildConfiguration.swift.in generated/BuildConfiguration.swift @ONLY)
set(ALRIGHT_SHARED src/core/DocumentCreator.swift src/core/DocumentKind.swift src/core/CanvasSize.swift src/core/PhotoshopDocument.swift src/core/IllustratorDocument.swift src/shared/FolderStore.swift "${CMAKE_BINARY_DIR}/generated/BuildConfiguration.swift")
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
    COMMAND AlrightIconGenerator "${CMAKE_BINARY_DIR}/generated/Alright.iconset"
    COMMAND /usr/bin/iconutil -c icns "${CMAKE_BINARY_DIR}/generated/Alright.iconset" -o "${ALRIGHT_ICON}"
    DEPENDS AlrightIconGenerator tools/GenerateIcon.swift VERBATIM)
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
    COMMAND /usr/bin/codesign --force --timestamp=none --options runtime --sign "${ALRIGHT_SIGNING_IDENTITY}"
        --entitlements "${CMAKE_BINARY_DIR}/FinderSync.entitlements" "$<TARGET_BUNDLE_DIR:AlrightFinderSync>"
    COMMAND /usr/bin/codesign --force --timestamp=none --options runtime --sign "${ALRIGHT_SIGNING_IDENTITY}"
        --entitlements "${CMAKE_BINARY_DIR}/App.entitlements" "$<TARGET_BUNDLE_DIR:Alright>"
    DEPENDS Alright AlrightFinderSync "${ALRIGHT_ICON}" ${ALRIGHT_OFFICE_OUTPUTS}
    VERBATIM)
add_custom_target(AlrightRegisterExtension
    COMMAND /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
        -f "$<TARGET_BUNDLE_DIR:Alright>"
    COMMAND /usr/bin/pluginkit -a "$<TARGET_BUNDLE_DIR:AlrightFinderSync>"
    DEPENDS AlrightBundle VERBATIM)

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
endif()

include(cmake/single-app/SingleApp.cmake)
cmake_language(DEFER CALL product_single_app Alright "bin")
