import Foundation
import Darwin

struct GrantedFolder: Codable, Equatable {
    let id: String
    let path: String
    let bookmark: Data
    let device: Int32
    let inode: UInt64
}
struct DocumentRequest: Codable {
    let id: String
    let folderID: String
    let path: String
    let created: Date
    let version: Int
    var kind: DocumentKind? = nil
    var canvas: CanvasSize? = nil
    var documentKind: DocumentKind { kind ?? .text }
}

final class FolderStore {
    static let changed = Notification.Name("com.iisacc.Alright.foldersChanged")
    let directory: URL
    init(directory: URL) { self.directory = directory }

    static func shared() throws -> FolderStore {
        guard let directory = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: BuildConfiguration.appGroup) else {
            throw AlrightError(message: "Shared storage is unavailable. Check app signing and the App Group.")
        }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return FolderStore(directory: directory)
    }
    private var configurationURL: URL { directory.appendingPathComponent("folders.plist") }
    var folders: [GrantedFolder] {
        guard let data = try? Data(contentsOf: configurationURL) else { return [] }
        return (try? PropertyListDecoder().decode([GrantedFolder].self, from: data)) ?? []
    }
    func save(_ folders: [GrantedFolder]) throws {
        let encoder = PropertyListEncoder()
        encoder.outputFormat = .binary
        try encoder.encode(folders).write(to: configurationURL, options: .atomic)
        DistributedNotificationCenter.default().postNotificationName(Self.changed, object: nil, userInfo: nil, deliverImmediately: true)
    }
    func add(_ url: URL) throws {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }
        let canonical = url.resolvingSymlinksInPath().standardizedFileURL
        var info = stat()
        guard stat(canonical.path, &info) == 0, info.st_mode & S_IFMT == S_IFDIR else {
            throw AlrightError(message: "Choose an accessible folder.")
        }
        let bookmark = try canonical.bookmarkData(options: .withSecurityScope, includingResourceValuesForKeys: nil, relativeTo: nil)
        var entries = folders
        guard !entries.contains(where: { $0.path == canonical.path }) else { return }
        entries.append(GrantedFolder(id: UUID().uuidString, path: canonical.path, bookmark: bookmark, device: info.st_dev, inode: info.st_ino))
        try save(entries)
    }
    func remove(id: String) throws { try save(folders.filter { $0.id != id }) }
    func folder(containing path: String) -> GrantedFolder? {
        folders.filter { path == $0.path || path.hasPrefix($0.path == "/" ? "/" : $0.path + "/") }
            .max { $0.path.count < $1.path.count }
    }
    func enqueue(path: String, folderID: String, kind: DocumentKind = .text, canvas: CanvasSize = CanvasSize.atPointer()) throws -> URL {
        let request = DocumentRequest(id: UUID().uuidString, folderID: folderID, path: path, created: Date(), version: 3, kind: kind, canvas: canvas)
        let encoder = PropertyListEncoder()
        encoder.outputFormat = .binary
        try encoder.encode(request).write(to: file(request.id, suffix: "request"), options: .withoutOverwriting)
        return URL(string: "alright://create-document/" + request.id)!
    }
    private func file(_ id: String, suffix: String) -> URL { directory.appendingPathComponent(id + "." + suffix) }
    func claim(_ url: URL) throws -> DocumentRequest {
        let id = url.lastPathComponent
        guard url.scheme == "alright", ["new-text", "create-document"].contains(url.host ?? ""), url.query == nil, url.fragment == nil,
              url.user == nil, url.password == nil, url.port == nil,
              UUID(uuidString: id) != nil, url.path == "/" + id else {
            throw AlrightError(message: "Invalid Finder request.")
        }
        let claimed = file(id, suffix: "processing")
        guard renamex_np(file(id, suffix: "request").path, claimed.path, UInt32(RENAME_EXCL)) == 0 else {
            throw AlrightError(message: "This Finder request is missing or has already been handled.")
        }
        do {
            let request = try PropertyListDecoder().decode(DocumentRequest.self, from: Data(contentsOf: claimed))
            guard request.id == id,
                  (request.version == 1 && request.kind == nil) || (request.version == 2 && request.kind != nil) || (request.version == 3 && request.kind != nil && request.canvas != nil), abs(request.created.timeIntervalSinceNow) <= 300 else {
                throw AlrightError(message: "The Finder request expired or is invalid. Choose a document from Alright again.")
            }
            if let canvas = request.canvas { try canvas.validate() }
            return request
        } catch {
            try? FileManager.default.removeItem(at: claimed)
            throw error
        }
    }
    func finish(_ request: DocumentRequest) { try? FileManager.default.removeItem(at: file(request.id, suffix: "processing")) }
    func resolve(_ folder: GrantedFolder) throws -> URL {
        var stale = false
        let url = try URL(resolvingBookmarkData: folder.bookmark, options: [.withSecurityScope, .withoutUI], relativeTo: nil, bookmarkDataIsStale: &stale)
        guard !stale, url.path == folder.path else {
            throw AlrightError(message: "Folder access changed. Remove this folder and add it again.")
        }
        return url
    }
}
