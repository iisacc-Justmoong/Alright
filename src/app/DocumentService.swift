import Foundation
import Darwin

struct DocumentService {
    var templates: URL = Bundle.main.resourceURL!.appendingPathComponent("DocumentTemplates")
    let store: FolderStore
    func create(requestURL: URL) throws -> URL {
        let request = try store.claim(requestURL)
        defer { store.finish(request) }
        guard let folder = store.folder(containing: request.path), folder.id == request.folderID else {
            throw AlrightError(message: "This folder is no longer registered. Add it in Alright again.")
        }
        let root = try store.resolve(folder)
        guard root.startAccessingSecurityScopedResource() else {
            throw AlrightError(message: "Folder access was denied. Remove the folder and add it again.")
        }
        defer { root.stopAccessingSecurityScopedResource() }
        var info = stat()
        guard stat(root.path, &info) == 0, info.st_dev == folder.device, info.st_ino == folder.inode else {
            throw AlrightError(message: "The registered folder was replaced or moved. Add it again.")
        }
        let relative = request.path == root.path ? "" : String(request.path.dropFirst(root.path == "/" ? 1 : root.path.count + 1))
        let kind = request.documentKind
        let content = try kind.contents(templates: templates, canvas: request.canvas ?? CanvasSize.atPointer())
        let created = try DocumentCreator.create(root: root.path, relative: relative, kind: kind, content: content)
        return created
    }
}
