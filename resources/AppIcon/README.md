# Alright app icon

`Alright.ai` is the editable Adobe Illustrator master. `Alright.svg` is its portable vector export, and `Alright.png` is the 1024 × 1024 opaque RGB export used by the build. The blue background fills the entire square; it has no outer border, white margin, or pre-applied corner mask. The folded document and green add badge are editable paths and gradients, without embedded raster images or fonts.

To update all three files, edit and save `Alright.ai` in Illustrator, then choose **File → Scripts → Other Script…** and select `tools/ExportAppIcon.jsx` from this repository. The script preserves the native AI master, refreshes the SVG and PNG, and leaves the AI document open. Only when the AI file does not yet exist does it import the SVG to create it. Other open Illustrator documents are left untouched.

The script checks the 1024 × 1024 artboard and rejects embedded or linked raster artwork. Its export evidence is written to `build/icon-review/illustrator-export.json`. The original 2026-10-09 export used Adobe Illustrator 30.8.1, with 44 editable paths, zero raster items, and zero placed items.

Run `cmake --build build` and `ctest --test-dir build --output-on-failure` after export. The build resamples `Alright.png` into all ten macOS iconset representations and embeds `Alright.icns` in the canonical `build/bin/Alright.app`. The bundle test checks dimensions, opacity, the unchanged 1024-pixel representation, ICNS contents, and the exact generated-to-bundled icon match. Rebuild `AlrightAppStorePackage` when refreshing an existing App Store installer package.

## 2026-10-15 icon refresh

The current three masters are byte-for-byte copies of the user-selected `Glossy-Blue-File-Add.ai`, `.svg`, and `.png` in Workspace `build/app-icon-20261015/`. The 1024 × 1024 RGB PNG is opaque and fills the square without an outer border. The new Illustrator evidence records 88 editable paths, 13 gradient paths, no stroked paths, and no raster or placed items. Original icon files and working-tree changes are preserved in `build/verification/icon-submission-20261015/`; the source hashes are recorded there in `icon-sources.json`. Version 0.6.1 build 9 is the new submission candidate.
