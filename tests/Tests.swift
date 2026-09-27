import AppKit
import FinderSync
import Darwin
import PDFKit
import ImageIO

func check(_ condition: @autoclosure () throws -> Bool, _ message: String) throws {
    if try !condition() { throw AlrightError(message: "TEST FAILED: " + message) }
}
func rejects(_ message: String, _ body: () throws -> Void) throws {
    do { try body() } catch { return }
    throw AlrightError(message: "TEST FAILED: accepted " + message)
}

@main struct Tests {
    @MainActor static func main() throws {
        let suite = CommandLine.arguments[1]
        let root = URL(fileURLWithPath: CommandLine.arguments[2]).appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        switch suite {
        case "NewText": try testNewText(root)
        case "Documents": try testDocuments(root, templates: URL(fileURLWithPath: CommandLine.arguments[3]))
        case "Requests": try testRequests(root)
        case "FinderMenu": try testMenu(root)
        case "AppLifecycle": try testApp(root)
        default: throw AlrightError(message: "Unknown test suite")
        }
        print("PASS \(suite)")
    }
    static func testNewText(_ root: URL) throws {
        let folder = root.appendingPathComponent("한글 ' $ ` test")
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        let first = try DocumentCreator.create(root: root.path, relative: folder.lastPathComponent)
        try check(first.lastPathComponent == "New Text.txt", "initial name")
        try check(Data(contentsOf: first).isEmpty, "empty file")
        let original = Data("preserve original content".utf8)
        try original.write(to: first)
        let second = try DocumentCreator.create(root: root.path, relative: folder.lastPathComponent)
        try check(second.lastPathComponent == "New Text 2.txt", "collision suffix")
        try check(Data(contentsOf: first) == original, "never overwrite")
        try rejects("parent traversal") { _ = try DocumentCreator.create(root: root.path, relative: "../escape") }
        try rejects("absolute relative path") { _ = try DocumentCreator.create(root: root.path, relative: folder.path) }
        try rejects("missing directory") { _ = try DocumentCreator.create(root: root.path, relative: "missing") }
        try rejects("file as root") { _ = try DocumentCreator.create(root: first.path, relative: "") }
        try rejects("embedded NUL") { _ = try DocumentCreator.create(root: root.path, relative: "\0") }
        let link = root.appendingPathComponent("link")
        try FileManager.default.createSymbolicLink(at: link, withDestinationURL: folder)
        try rejects("symlink directory") { _ = try DocumentCreator.create(root: root.path, relative: "link") }
        try rejects("symlink root") { _ = try DocumentCreator.create(root: link.path, relative: "") }
        try FileManager.default.createSymbolicLink(at: root.appendingPathComponent("New Text.txt"), withDestinationURL: first)
        let afterLink = try DocumentCreator.create(root: root.path, relative: "")
        try check(afterLink.lastPathComponent == "New Text 2.txt", "symlink filename collision")
        let concurrent = root.appendingPathComponent("concurrent")
        try FileManager.default.createDirectory(at: concurrent, withIntermediateDirectories: true)
        DispatchQueue.concurrentPerform(iterations: 16) { _ in
            // Any failure aborts the test executable; exclusive creation must tolerate races.
            _ = try! DocumentCreator.create(root: concurrent.path, relative: "")
        }
        let files = try FileManager.default.contentsOfDirectory(at: concurrent, includingPropertiesForKeys: nil)
        try check(files.count == 16, "16 concurrent unique files")
        for file in files { try check(Data(contentsOf: file).isEmpty, "concurrent empty file") }
    }
    static func testDocuments(_ root: URL, templates: URL) throws {
        for kind in DocumentKind.allCases {
            let content = try kind.contents(templates: templates)
            let file = try DocumentCreator.create(root: root.path, relative: "", kind: kind, content: content)
            try check(file.pathExtension == kind.fileExtension, "document extension")
            try check(Data(contentsOf: file) == content, "complete document bytes")
            let second = try DocumentCreator.create(root: root.path, relative: "", kind: kind, content: content)
            try check(second.lastPathComponent == kind.title + " 2." + kind.fileExtension, "per-format collision")
            switch kind {
            case .text, .markdown, .csv: try check(content.isEmpty, "blank text document")
            case .word, .excel, .powerpoint, .openDocumentText, .openDocumentSpreadsheet, .openDocumentPresentation:
                try check(content.count > 22 && content.starts(with: [0x50, 0x4b, 0x03, 0x04]), "Office package signature")
            case .json: try check((JSONSerialization.jsonObject(with: content) as? [String: String]) == [:], "valid empty JSON")
            case .richText:
                let document = NSAttributedString(rtf: content, documentAttributes: nil)
                try check(document != nil && document!.string.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty, "valid blank RTF")
            case .pdf, .illustrator:
                let pdf = PDFDocument(data: content)
                try check(pdf?.pageCount == 1, "valid single-page PDF-compatible document")
                if kind == .illustrator {
                    try check(content.range(of: Data("/PieceInfo".utf8)) != nil && content.range(of: Data("/Illustrator".utf8)) != nil, "native Illustrator editing data")
                }
            case .photoshop:
                let image = CGImageSourceCreateWithData(content as CFData, nil)!
                let properties = CGImageSourceCopyPropertiesAtIndex(image, 0, nil)! as NSDictionary
                try check(properties[kCGImagePropertyPixelWidth] as? Int == 1920 && properties[kCGImagePropertyPixelHeight] as? Int == 1080, "PSD canvas dimensions")
                try check(CGImageSourceCreateImageAtIndex(image, 0, nil) != nil, "PSD decodes")
            case .svg:
                let parser = XMLParser(data: content)
                try check(parser.parse(), "valid SVG XML")
            case .html: try check(String(decoding: content, as: UTF8.self).contains("<!doctype html>"), "HTML document")
            }
        }
        for size in [CanvasSize(width: 5120, height: 2880), CanvasSize(width: 1513, height: 983), CanvasSize(width: 1080, height: 1920), CanvasSize(width: 1, height: 1)] {
            let psd = try DocumentKind.photoshop.contents(templates: templates, canvas: size)
            let image = CGImageSourceCreateWithData(psd as CFData, nil)!
            let props = CGImageSourceCopyPropertiesAtIndex(image, 0, nil)! as NSDictionary
            try check(props[kCGImagePropertyPixelWidth] as? Int == size.width && props[kCGImagePropertyPixelHeight] as? Int == size.height, "dynamic PSD dimensions")
            try check(CGImageSourceCreateImageAtIndex(image, 0, nil) != nil, "odd-width PSD decodes")
            let ai = try DocumentKind.illustrator.contents(templates: templates, canvas: size)
            let bounds = PDFDocument(data: ai)!.page(at: 0)!.bounds(for: .mediaBox)
            try check(bounds.width == CGFloat(size.width) && bounds.height == CGFloat(size.height), "AI PDF artboard dimensions")
            try check(ai.range(of: Data("%_\(size.width) -\(size.height) /RealPointRelToROrigin".utf8)) != nil, "AI native artboard matches PDF")
        }
        for size in [CanvasSize(width: 0, height: 1), CanvasSize(width: 1, height: -1), CanvasSize(width: 16384, height: 1)] {
            try rejects("invalid PSD dimensions") { _ = try PhotoshopDocument.contents(size: size) }
            try rejects("invalid AI dimensions") { _ = try IllustratorDocument.contents(size: size, templates: templates) }
        }
        let remaining = try FileManager.default.contentsOfDirectory(atPath: root.path)
        try check(!remaining.contains { $0.hasPrefix(".alright-") }, "no temporary documents left")
        for kind in [DocumentKind.word, .excel, .powerpoint, .openDocumentText, .openDocumentSpreadsheet, .openDocumentPresentation] {
            try rejects("missing Office template") { _ = try kind.contents(templates: root) }
            try Data("invalid".utf8).write(to: root.appendingPathComponent("Blank." + kind.fileExtension))
            try rejects("damaged Office template") { _ = try kind.contents(templates: root) }
        }
        try rejects("missing Adobe template") { _ = try DocumentKind.illustrator.contents(templates: root) }
    }
    static func store(_ root: URL) throws -> FolderStore {
        let store = FolderStore(directory: root)
        // PropertyListSerialization reproduces the pre-Swift dictionary/NSNumber schema.
        let entries: [[String: Any]] = [
            ["id": "root", "path": root.path, "bookmark": Data([1]), "device": NSNumber(value: 1), "inode": NSNumber(value: UInt64.max)],
            ["id": "nested", "path": root.path + "/nested", "bookmark": Data([2]), "device": NSNumber(value: 1), "inode": NSNumber(value: 2)]
        ]
        try PropertyListSerialization.data(fromPropertyList: entries, format: .binary, options: 0).write(to: root.appendingPathComponent("folders.plist"))
        return store
    }
    static func testRequests(_ root: URL) throws {
        let store = try store(root)
        try check(store.folders.count == 2 && store.folders[0].inode == UInt64.max, "legacy schema compatibility")
        try check(store.folder(containing: root.path + "/nested/child")?.id == "nested", "longest matching root")
        try check(store.folder(containing: root.path + "-other") == nil, "component boundary")
        let url = try store.enqueue(path: root.path + "/nested/a", folderID: "nested")
        let request = try store.claim(url)
        try check(request.path == root.path + "/nested/a", "captured request path")
        try rejects("second claim") { _ = try store.claim(url) }
        store.finish(request)
        try rejects("replay") { _ = try store.claim(url) }
        try rejects("raw path URL") { _ = try store.claim(URL(string: "alright://new-text/../../tmp")!) }
        try rejects("missing request") { _ = try store.claim(URL(string: "alright://new-text/" + UUID().uuidString)!) }
        let expired = DocumentRequest(id: UUID().uuidString, folderID: "root", path: root.path, created: Date(timeIntervalSinceNow: -600), version: 1)
        try PropertyListEncoder().encode(expired).write(to: root.appendingPathComponent(expired.id + ".request"))
        try rejects("expired request") { _ = try store.claim(URL(string: "alright://new-text/" + expired.id)!) }
        try check(!FileManager.default.fileExists(atPath: root.appendingPathComponent(expired.id + ".processing").path), "expired cleanup")
        for kind in DocumentKind.allCases {
            let request = try store.claim(store.enqueue(path: root.path, folderID: "root", kind: kind))
            try check(request.version == 3 && request.documentKind == kind && request.canvas != nil, "request format round trip")
            store.finish(request)
        }
        let portrait = CanvasSize(width: 1440, height: 2560)
        let screenRequest = try store.claim(store.enqueue(path: root.path, folderID: "root", kind: .illustrator, canvas: portrait))
        try check(screenRequest.canvas == portrait, "screen snapshot survives host handoff")
        store.finish(screenRequest)
        let invalidScreen = try store.enqueue(path: root.path, folderID: "root", kind: .photoshop, canvas: CanvasSize(width: -1, height: 2880))
        try rejects("invalid persisted canvas") { _ = try store.claim(invalidScreen) }
        let version2 = DocumentRequest(id: UUID().uuidString, folderID: "root", path: root.path, created: Date(), version: 2, kind: .markdown)
        try PropertyListEncoder().encode(version2).write(to: root.appendingPathComponent(version2.id + ".request"))
        let previousRequest = try store.claim(URL(string: "alright://create-document/" + version2.id)!)
        try check(previousRequest.documentKind == .markdown && previousRequest.canvas == nil, "version 2 format compatibility")
        store.finish(previousRequest)
        let legacy = DocumentRequest(id: UUID().uuidString, folderID: "root", path: root.path, created: Date(), version: 1)
        try PropertyListEncoder().encode(legacy).write(to: root.appendingPathComponent(legacy.id + ".request"))
        let legacyClaim = try store.claim(URL(string: "alright://new-text/" + legacy.id)!)
        try check(legacyClaim.documentKind == .text, "legacy text request compatibility")
        store.finish(legacyClaim)
        for kind in ["unsupported", "../../evil"] {
            let id = UUID().uuidString
            let raw: [String: Any] = ["id": id, "folderID": "root", "path": root.path, "created": Date(), "version": 2, "kind": kind]
            try PropertyListSerialization.data(fromPropertyList: raw, format: .binary, options: 0).write(to: root.appendingPathComponent(id + ".request"))
            try rejects("unrecognized document format") { _ = try store.claim(URL(string: "alright://create-document/" + id)!) }
        }
        let revoked = try store.enqueue(path: root.path + "/nested", folderID: "nested")
        try store.remove(id: "nested")
        try rejects("revoked grant") { _ = try DocumentService(store: store).create(requestURL: revoked) }
        try check(store.folders.count == 1, "persistent removal")
    }
    @MainActor static func testMenu(_ root: URL) throws {
        _ = NSApplication.shared
        let store = try store(root)
        let extensionInstance = AlrightFinderSync(store: store)
        try check(extensionInstance.menu(directory: root, kind: .contextualMenuForItems) == nil, "no item menu")
        try check(extensionInstance.menu(directory: nil, kind: .contextualMenuForContainer) == nil, "no missing target")
        try check(extensionInstance.menu(directory: root.appendingPathExtension("outside"), kind: .contextualMenuForContainer) == nil, "no unregistered target")
        let menu = extensionInstance.menu(directory: root, kind: .contextualMenuForContainer)!
        try check(menu.items.count == 1 && menu.items[0].title == "Alright", "single branded submenu")
        let children = menu.items[0].submenu!.items.filter { !$0.isSeparatorItem }
        try check(children.map(\.title) == DocumentKind.allCases.map(\.menuTitle), "all document kinds in order")
        let first = children[0]
        let psd = children.first { $0.title == DocumentKind.photoshop.menuTitle }!
        let ai = children.first { $0.title == DocumentKind.illustrator.menuTitle }!
        _ = extensionInstance.menu(directory: root.appendingPathComponent("nested"), kind: .contextualMenuForContainer)
        let forwarded = NSMenuItem(title: first.title, action: first.action, keyEquivalent: "")
        forwarded.tag = first.tag
        try check(extensionInstance.consume(forwarded)?.path == root.path, "Finder tag preserves original menu target")
        try check(extensionInstance.consume(forwarded) == nil, "one-time menu snapshot")
        try check(first.title == "New Text (.txt)" && first.image != nil, "SF Symbol menu")
        for (item, expected) in [(psd, DocumentKind.photoshop), (ai, .illustrator)] {
            let forwarded = NSMenuItem()
            forwarded.tag = item.tag
            let snapshot = extensionInstance.consume(forwarded)
            try check(snapshot?.path == root.path && snapshot?.kind == expected, "format and path survive Finder forwarding")
        }
        for item in [menu.items[0]] + children {
            try check(item.image?.isTemplate == true, "template symbol available for " + item.title)
        }
        // Finder can flatten NSImage to pixels across its process boundary. Verify
        // that flattened symbols retain semantic text color even without metadata.
        let names = Set(DocumentKind.allCases.map(\.symbol) + ["doc.badge.plus"])
        for appearanceName in [NSAppearance.Name.aqua, .darkAqua,
                               .accessibilityHighContrastAqua, .accessibilityHighContrastDarkAqua] {
            let appearance = NSAppearance(named: appearanceName)!
            for name in names {
                var image: NSImage?
                var expected: NSColor?
                appearance.performAsCurrentDrawingAppearance {
                    image = FinderMenuSymbols.image(name, description: name)
                    expected = NSColor.labelColor.usingColorSpace(.deviceRGB)
                }
                guard let image, let expected, let data = image.tiffRepresentation,
                      let bitmap = NSBitmapImageRep(data: data) else {
                    throw AlrightError(message: "TEST FAILED: flattened SF Symbol " + name)
                }
                var visiblePixels = 0
                for y in 0..<bitmap.pixelsHigh {
                    for x in 0..<bitmap.pixelsWide {
                        guard let color = bitmap.colorAt(x: x, y: y)?.usingColorSpace(.deviceRGB),
                              color.alphaComponent > 0.5 else { continue }
                        visiblePixels += 1
                        try check(abs(color.redComponent - expected.redComponent) < 0.03 &&
                                  abs(color.greenComponent - expected.greenComponent) < 0.03 &&
                                  abs(color.blueComponent - expected.blueComponent) < 0.03,
                                  "semantic text color survives flattening: \(name), \(appearanceName)")
                    }
                }
                try check(visiblePixels > 4, "nonempty SF Symbol " + name)
            }
        }
    }
    @MainActor static func testApp(_ root: URL) throws {
        let app = NSApplication.shared
        let delegate = AppDelegate(store: try store(root))
        app.delegate = delegate
        delegate.applicationDidFinishLaunching(Notification(name: NSApplication.didFinishLaunchingNotification))
        let window = delegate.window!
        try check(window.title == "Alright" && window.isVisible, "visible native host")
        try check(!delegate.applicationShouldTerminateAfterLastWindowClosed(app), "last window lifetime")
        window.setContentSize(NSSize(width: 680, height: 500))
        let frame = window.frame
        window.close()
        _ = delegate.applicationShouldHandleReopen(app, hasVisibleWindows: false)
        try check(delegate.window === window && window.isVisible && window.frame == frame, "reopen same window and frame")
        delegate.showMainWindow(nil)
        try check(app.windows.filter { $0.title == "Alright" }.count == 1, "one host window")
        try check(app.mainMenu!.items[0].submenu!.items.contains { $0.keyEquivalent == "q" && $0.action == #selector(NSApplication.terminate(_:)) }, "standard Quit")
        for name in Symbols.all { try check(Symbols.image(name, description: name) != nil, "SF Symbol \(name)") }
        window.close()
    }
}
