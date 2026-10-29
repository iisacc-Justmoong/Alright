# Alright

**From the moment you create a file in Finder to the moment you organize it, it is a macOS utility that completes necessary tasks with a right-click.**

Brand slogan draft: **Alright. Right where you click.**

It is currently a macOS-only app whose workflow ends with **right-click an empty space in Finder → Alright → create a file → enter its name in Finder**. The direct distribution build starts Finder filename editing automatically. The App Store build selects the created file in Finder; press Return to edit its name. It supports 16 formats: TXT, Markdown, RTF, PDF, DOCX, XLSX, PPTX, ODT, ODS, ODP, JSON, CSV, HTML, SVG, Photoshop PSD, and Illustrator AI. It uses Swift 6, AppKit, and Finder Sync, and requires neither Qt nor an external runtime. The app icon uses the Illustrator artwork in `resources/AppIcon/`; screen and menu icons use SF Symbols.

<a id="빌드와-실행"></a>

## Build and run

To provide macOS, Swift   6, Xcode, CMake   3.24 or higher, Ninja, Python   3, and a valid macOS code signing certificate are required. Python Standard libraries are used only to package and test Office documents during build. The deployed app creates files without Python ·Office· LibreOffice installation. Run from the project directory.

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON -DALRIGHT_APP_STORE=OFF
cmake --build build
ctest --test-dir build --output-on-failure
cmake --build build --target AlrightRegisterExtension
open build/bin/Alright.app
```

When switching to an existing Unix Makefiles build tree, run one time   `cmake --fresh -S . -B build -G Ninja` initially. Swift Intermediate files for module, debug symbols, and icon creation are also placed in `build/`.

The editable app icon is `resources/AppIcon/Alright.ai`, with a vector SVG copy and a 1024 × 1024 PNG master alongside it. The PNG fills the complete square with opaque artwork, without an outer border or transparent padding. `AlrightIconGenerator` resamples this master into the ten standard iconset representations, and `iconutil` packages them into the app's `Alright.icns`. Re-exporting the PNG from Illustrator and rebuilding updates the bundled icon before signing. `Alright.Bundle` validates the master's dimensions and opacity, every generated representation, and the generated-to-bundled ICNS identity.

The host bundle declares `CFBundleIcons → CFBundlePrimaryIcon → CFBundleSymbolName = folder` for Finder's sidebar. Registered folders such as Workspace display the native folder SF Symbol. `Alright.Bundle` checks this declaration together with the application's ICNS artwork so rebuilding cannot replace folder symbols with the Alright app icon.

The default signing configuration is the `Developer ID Application: MUYEONG YUN (5U49ST9XZH)` held locally. In other development environments, CMake's `ALRIGHT_SIGNING_IDENTITY` and `ALRIGHT_TEAM_ID` are specified together. Since apps and extensions from the same team share a container, ad-hoc signing is not used as a replacement. Set `ALRIGHT_APP_STORE=ON` for the sandboxed App Store workflow and use an Apple Distribution app signing identity. The signed installer package uses a separate Mac Installer Distribution identity. Build and package instructions are in [App Store distribution](docs/AppStoreDistribution.md).

1. Enable the Alright extension in `Finder Extension Settings…`. Registration and activation have been completed on the current development computer.
2. Select a folder to use as `Add Folder…` and grant read/write permissions. The selected folder and subfolders are the targets.
3. In a direct distribution build, set the macOS accessibility permission required for automatic Finder name editing in `Enable Filename Editing…`. The App Store build does not request this permission.
4. Open the folder in Finder and **right-click empty space → Alright → select desired document type**.
5. The direct distribution build starts filename editing in Finder. In the App Store build, the created file is selected in Finder; press Return to edit its name. If the name already exists, ` 2` and ` 3` are appended. TXT is 0 bytes and PSD ·AI is created with the pixel size of the right-clicked screen. The editor is not automatically opened. Initial content by format is specified in [document creation](docs/DocumentCreation.md).

`Remove` removes folder registration and access permissions saved by the app. User files are not deleted. Closing the window or `⌘W` closes only the window, while `⌘Q` exits the app. Even if the app is terminated, it is re-executed by the New Text request of the active Finder extension.

The only app bundle is `build/bin/Alright.app` and the Finder extension is the internal `Contents/PlugIns/AlrightFinderSync.appex`. Direct distribution uses Developer ID signing and hardened runtime; the Finder extension maintains App Sandbox, while the host uses accessibility permissions for automatic Finder name editing. App Store distribution enables App Sandbox for both bundles and uses Finder selection with manual Return instead of Accessibility APIs. Its signed `.pkg` is created directly from the canonical app and saved in `build/appstore/`. Full disk access and Apple Events automation permissions are not required. Local direct builds omit timestamps and notarization. App Store upload and review are separate from local build, test, and package signature verification. Current behavior and constraints are specified in [document creation](docs/DocumentCreation.md) and [App Store distribution](docs/AppStoreDistribution.md).

|Document|Content|
| --- | --- |
|[Product and Technology Blueprint](docs/BLUEPRINT.md)|User, feature scope, right-click structure, native architecture, SDK utilization, monetization|
|[Execution and Verification Plan](docs/DELIVERY.md)|Technical proof, implementation order, acceptance criteria, failure handling, release gate|
|[Finder New Text Implementation](docs/FinderNewText.md)|Permission and extension structure, testing, actual Finder execution evidence|
|[Various Document Creation](docs/DocumentCreation.md)|Alright submenu, 16 format, screen size, Finder name edit|
|[Create Office document](docs/OfficeDocuments.md)|DOCX · XLSX · PPTX · ODT · ODS · ODP ,  XML  original and packaging/verification|
|[Hello World implementation](docs/HelloWorld.md)|Past verification record of initial host app implementation|
|[Single app build](docs/SingleAppBuild.md)|Output path, rebuild/sign rules|
|[App Store distribution](docs/AppStoreDistribution.md)|Sandboxed Finder workflow, distribution signing, installer package and verification|

<a id="핵심-결정"></a>

## Core decision

- The product is a macOS -specific Finder extension. It focuses on file creation, path copy, and destination copy/move.
- First validate Finder Sync's suitability, exposure scope, and permission transfer. It does not guarantee behavior in all folders.
- File creation, permission storage, AppKit   UI , and implement the Finder Sync extension as Swift   6 . No Qt dependencies are introduced.
- Basic file operations work without accounts and servers. Paid features and pricing are business hypotheses to validate.
- Create documents in the registered folder. 0.5.0 ends with Finder name editing. PSD · AI format is verified with Photoshop ·Illustrator. Path copy, file copy, and move are subsequent scopes.

Blueprint creation date: 2026-09-20. Swift transition date: 2026-09-25. Facts verified in technical documentation, product design hypotheses, and unverified items are distinguished in each document.

<!-- workspace-docs:readme:start -->
## Documentation entry points

- Human overview: this English `README.md`.
- Agent instructions: [AGENT.md](AGENT.md).
- Human documentation: [documentation index](docs/README.md).
- Structured agent documentation: [agent index](docs/agent-index.json).
<!-- workspace-docs:readme:end -->
