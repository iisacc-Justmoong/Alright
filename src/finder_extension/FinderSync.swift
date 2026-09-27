import AppKit
import FinderSync

@objc(AlrightFinderSync)
final class AlrightFinderSync: FIFinderSync {
    private let store: FolderStore?
    private var targets: [Int: (path: String, folderID: String, kind: DocumentKind, canvas: CanvasSize)] = [:]
    private var nextTag = 0

    override init() {
        store = try? FolderStore.shared()
        super.init()
        reloadFolders()
        DistributedNotificationCenter.default().addObserver(self, selector: #selector(reloadFolders), name: FolderStore.changed, object: nil)
    }
    init(store: FolderStore) { self.store = store; super.init() }
    deinit { DistributedNotificationCenter.default().removeObserver(self) }
    @objc private func reloadFolders() {
        FIFinderSyncController.default().directoryURLs = Set((store?.folders ?? []).map { URL(fileURLWithPath: $0.path) })
    }
    override func menu(for menuKind: FIMenuKind) -> NSMenu? {
        menu(directory: FIFinderSyncController.default().targetedURL(), kind: menuKind)
    }
    func menu(directory: URL?, kind: FIMenuKind) -> NSMenu? {
        guard kind == .contextualMenuForContainer, let directory, directory.isFileURL,
              let folder = store?.folder(containing: directory.path) else { return nil }
        let menu = NSMenu(title: "Alright")
        let group = menu.addItem(withTitle: "Alright", action: nil, keyEquivalent: "")
        group.image = FinderMenuSymbols.image("doc.badge.plus", description: "Alright")
        let submenu = NSMenu(title: "Alright")
        group.submenu = submenu
        let canvas = CanvasSize.atPointer()
        for kind in DocumentKind.allCases {
            if kind == .word || kind == .openDocumentText || kind == .json || kind == .photoshop { submenu.addItem(.separator()) }
            nextTag += 1
            targets[nextTag] = (directory.path, folder.id, kind, canvas)
            // Keep 64 complete menus, including every document type in each menu.
            targets.removeValue(forKey: nextTag - 64 * DocumentKind.allCases.count)
            let item = submenu.addItem(withTitle: kind.menuTitle, action: #selector(newDocument(_:)), keyEquivalent: "")
            item.target = self
            item.tag = nextTag
            item.image = FinderMenuSymbols.image(kind.symbol, description: kind.title)
        }
        return menu
    }
    func consume(_ item: NSMenuItem) -> (path: String, folderID: String, kind: DocumentKind, canvas: CanvasSize)? {
        // Finder reconstructs NSMenuItem across processes; only its integer tag survives.
        targets.removeValue(forKey: item.tag)
    }
    @objc private func newDocument(_ item: NSMenuItem) {
        guard let target = consume(item), let store else { return }
        do {
            let url = try store.enqueue(path: target.path, folderID: target.folderID, kind: target.kind, canvas: target.canvas)
            let configuration = NSWorkspace.OpenConfiguration()
            configuration.activates = false
            NSWorkspace.shared.open(url, configuration: configuration) { _, error in
                if let error { NSLog("Alright: %@", error.localizedDescription) }
            }
        } catch {
            NSLog("Alright: %@", error.localizedDescription)
            let message = error.localizedDescription
            Task { @MainActor in
                let alert = NSAlert()
                alert.messageText = "Document creation could not finish"
                alert.informativeText = message
                alert.runModal()
            }
        }
    }
}

enum FinderMenuSymbols {
    static func image(_ name: String, description: String) -> NSImage? {
        guard let symbol = NSImage(systemSymbolName: name, accessibilityDescription: description)?
            .withSymbolConfiguration(.preferringMonochrome()) else { return nil }
        let image = NSImage(size: symbol.size)
        image.lockFocus()
        symbol.draw(in: NSRect(origin: .zero, size: symbol.size))
        NSColor.labelColor.setFill()
        NSRect(origin: .zero, size: symbol.size).fill(using: .sourceIn)
        image.unlockFocus()
        // Finder's menu transport on macOS 27 does not apply template tinting.
        // Bake in the current semantic text color each time a menu is requested;
        // retain template metadata for renderers that do support native tinting.
        image.isTemplate = true
        image.accessibilityDescription = description
        return image
    }
}
