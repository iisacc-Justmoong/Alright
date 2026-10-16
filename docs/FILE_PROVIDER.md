# File creation ownership in Alright

Finder document creation and shared folder/request persistence compile the native Swift provider. Granted-root traversal, no-follow opening and exclusive document naming preserve existing documents.

The common [ownership contract](../../../../SDK/iiFileProvider/docs/FILE_OWNERSHIP.md) defines stream, staging, control-file and
installed-package rules. Source regression tests remain with this module; the
workspace creation audit also checks these boundaries. Build/deployment and target
runtime validation are separate evidence.

Changed boundaries:


- `src/core/DocumentCreator.swift`
- `src/shared/FolderStore.swift`
