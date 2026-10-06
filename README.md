# Alright

**From the moment you create a file in Finder to the moment you organize it, it is a macOS utility that completes necessary tasks with a right-click.**

Brand slogan draft: **Alright. Right where you click.**

It is currently a macOS-only app whose workflow ends with **right-click an empty space in Finder → Alright → create a file → enter its name in Finder**. It supports 16 formats: TXT, Markdown, RTF, PDF, DOCX, XLSX, PPTX, ODT, ODS, ODP, JSON, CSV, HTML, SVG, Photoshop PSD, and Illustrator AI. It uses Swift 6, AppKit, and Finder Sync, and requires neither Qt nor an external runtime. App, screen, and menu icons use SF Symbols.

<a id="빌드와-실행"></a>

## Build and run

To provide macOS, Swift   6, Xcode, CMake   3.24 or higher, Ninja, Python   3, and a valid macOS code signing certificate are required. Python Standard libraries are used only to package and test Office documents during build. The deployed app creates files without Python ·Office· LibreOffice installation. Run from the project directory.

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build --output-on-failure
cmake --build build --target AlrightRegisterExtension
open build/bin/Alright.app
```

When switching to an existing Unix Makefiles build tree, run one time   `cmake --fresh -S . -B build -G Ninja` initially. Swift Intermediate files for module, debug symbols, and icon creation are also placed in `build/`.

The default signing configuration is the `Developer ID Application: MUYEONG YUN (5U49ST9XZH)` held locally. In other development environments, CMake's `ALRIGHT_SIGNING_IDENTITY` and `ALRIGHT_TEAM_ID` are specified together. Since apps and extensions from the same team share a container, ad-hoc signing is not used as a replacement.

1. Enable the Alright extension in `Finder Extension Settings…`. Registration and activation have been completed on the current development computer.
2. Select a folder to use as `Add Folder…` and grant read/write permissions. The selected folder and subfolders are the targets.
3. Set the macOS accessibility permission required for Finder name editing in `Enable Filename Editing…`.
4. Open the folder in Finder and **right-click empty space → Alright → select desired document type**.
5. The file is created and enters a state where the name is entered in Finder. If the name already exists, ` 2` and ` 3` are appended. TXT is 0 bytes and PSD ·AI is created with the pixel size of the right-clicked screen. The editor is not automatically opened. Initial content by format is specified in [document creation](docs/DocumentCreation.md).

`Remove` removes folder registration and access permissions saved by the app. User files are not deleted. Closing the window or `⌘W` closes only the window, while `⌘Q` exits the app. Even if the app is terminated, it is re-executed by the New Text request of the active Finder extension.

The only app deliverable is `build/bin/Alright.app` and the Finder extension is the internal `Contents/PlugIns/AlrightFinderSync.appex`. Developer ID signature and hardened runtime are applied. The Finder extension maintains App Sandbox and the host uses accessibility permissions for Finder name editing. Local builds omit timestamps and notarization. Full disk access and Apple Events automation permissions are not required. Current behavior and constraints are specified in [document creation](docs/DocumentCreation.md).

|Document|Content|
| --- | --- |
|[Product and Technology Blueprint](docs/BLUEPRINT.md)|User, feature scope, right-click structure, native architecture, SDK utilization, monetization|
|[Execution and Verification Plan](docs/DELIVERY.md)|Technical proof, implementation order, acceptance criteria, failure handling, release gate|
|[Finder New Text Implementation](docs/FinderNewText.md)|Permission and extension structure, testing, actual Finder execution evidence|
|[Various Document Creation](docs/DocumentCreation.md)|Alright submenu, 16 format, screen size, Finder name edit|
|[Create Office document](docs/OfficeDocuments.md)|DOCX · XLSX · PPTX · ODT · ODS · ODP ,  XML  original and packaging/verification|
|[Hello World implementation](docs/HelloWorld.md)|Past verification record of initial host app implementation|
|[Single app build](docs/SingleAppBuild.md)|Output path, rebuild/sign rules|

<a id="핵심-결정"></a>

## Core decision

- The product is a macOS -specific Finder extension. It focuses on file creation, path copy, and destination copy/move.
- First validate Finder Sync's suitability, exposure scope, and permission transfer. It does not guarantee behavior in all folders.
- File creation, permission storage, AppKit   UI , and implement the Finder Sync extension as Swift   6 . No Qt dependencies are introduced.
- Basic file operations work without accounts and servers. Paid features and pricing are business hypotheses to validate.
- Create documents in the registered folder. 0.5.0 ends with Finder name editing. PSD · AI format is verified with Photoshop ·Illustrator. Path copy, file copy, and move are subsequent scopes.

Blueprint creation date: 2026-09-20. Swift transition date: 2026-09-25. Facts verified in technical documentation, product design hypotheses, and unverified items are distinguished in each document.
