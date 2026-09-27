import AppKit
import FinderSync

@MainActor final class AppDelegate: NSObject, NSApplicationDelegate {
    private(set) var window: NSWindow?
    private var store: FolderStore?
    private var receivedFinderRequest = false
    private var creationTask: Task<Void, Never>?
    private let folderPicker = NSPopUpButton(frame: .zero, pullsDown: false)
    private let statusLabel = NSTextField(labelWithString: "")
    private let resultLabel = NSTextField(wrappingLabelWithString: "Add a folder, then right-click empty space inside it and choose Alright → a document type.")

    init(store: FolderStore? = nil) { self.store = store; super.init() }
    private func prepareStore() {
        guard store == nil else { return }
        do { store = try FolderStore.shared() } catch { NSLog("Alright: %@", error.localizedDescription) }
    }
    func applicationWillFinishLaunching(_ notification: Notification) { prepareStore() }
    func applicationDidFinishLaunching(_ notification: Notification) {
        prepareStore()
        let bar = NSMenu()
        let appMenu = NSMenu(title: "Alright")
        appMenu.addItem(withTitle: "About Alright", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide Alright", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Quit Alright", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        bar.addItem(withTitle: "Alright", action: nil, keyEquivalent: "").submenu = appMenu
        let windows = NSMenu(title: "Window")
        let show = windows.addItem(withTitle: "Show Alright", action: #selector(showMainWindow(_:)), keyEquivalent: "0")
        show.target = self
        windows.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windows.addItem(withTitle: "Close", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        bar.addItem(withTitle: "Window", action: nil, keyEquivalent: "").submenu = windows
        NSApp.mainMenu = bar
        NSApp.windowsMenu = windows
        if !receivedFinderRequest { showMainWindow(nil) }
    }
    private func button(_ title: String, symbol: String, action: Selector) -> NSButton {
        let button = NSButton(title: title, target: self, action: action)
        button.bezelStyle = .rounded
        button.image = Symbols.image(symbol, description: title)
        button.imagePosition = .imageLeading
        return button
    }
    @objc func showMainWindow(_ sender: Any?) {
        if window == nil {
            let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 530), styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
            self.window = window
            window.title = "Alright"
            window.isReleasedWhenClosed = false
            window.contentMinSize = NSSize(width: 600, height: 510)
            window.center()
            let icon = NSImageView(image: Symbols.image(Symbols.newText, description: "New Document")!)
            icon.symbolConfiguration = NSImage.SymbolConfiguration(pointSize: 44, weight: .regular)
            icon.contentTintColor = .controlAccentColor
            icon.setAccessibilityIdentifier("new-document-symbol")
            let title = NSTextField(labelWithString: "New Document")
            title.font = .systemFont(ofSize: 32, weight: .bold)
            title.setAccessibilityIdentifier("new-document-title")
            let description = NSTextField(wrappingLabelWithString: "Create a document, type its name in Finder, and you’re done.")
            description.alignment = .center
            description.textColor = .secondaryLabelColor
            description.widthAnchor.constraint(equalToConstant: 490).isActive = true
            statusLabel.setAccessibilityIdentifier("extension-status")
            folderPicker.setAccessibilityLabel("Allowed folders")
            folderPicker.widthAnchor.constraint(equalToConstant: 490).isActive = true
            let actions = NSStackView(views: [
                button("Add Folder…", symbol: Symbols.addFolder, action: #selector(addFolder(_:))),
                button("Remove", symbol: Symbols.remove, action: #selector(removeFolder(_:))),
                button("Open in Finder", symbol: Symbols.folder, action: #selector(revealFolder(_:)))
            ])
            actions.spacing = 8
            resultLabel.alignment = .center
            resultLabel.textColor = .secondaryLabelColor
            resultLabel.widthAnchor.constraint(equalToConstant: 490).isActive = true
            let stack = NSStackView(views: [icon, title, description, statusLabel,
                button("Finder Extension Settings…", symbol: Symbols.settings, action: #selector(manageExtension(_:))),
                button("Enable Filename Editing…", symbol: "pencil", action: #selector(enableFilenameEditing(_:))),
                folderPicker, actions, resultLabel])
            stack.orientation = .vertical
            stack.alignment = .centerX
            stack.spacing = 16
            stack.translatesAutoresizingMaskIntoConstraints = false
            let content = window.contentView!
            content.addSubview(stack)
            NSLayoutConstraint.activate([
                stack.centerXAnchor.constraint(equalTo: content.centerXAnchor),
                stack.centerYAnchor.constraint(equalTo: content.centerYAnchor),
                stack.leadingAnchor.constraint(greaterThanOrEqualTo: content.leadingAnchor, constant: 24),
                stack.trailingAnchor.constraint(lessThanOrEqualTo: content.trailingAnchor, constant: -24)
            ])
        }
        refreshStatus()
        if window!.isMiniaturized { window!.deminiaturize(nil) }
        window!.makeKeyAndOrderFront(nil)
        NSApp.activate()
    }
    private func refreshStatus() {
        let selected = folderPicker.selectedItem?.representedObject as? String
        folderPicker.removeAllItems()
        for folder in store?.folders ?? [] {
            folderPicker.addItem(withTitle: folder.path)
            folderPicker.lastItem?.representedObject = folder.id
            folderPicker.lastItem?.image = Symbols.image(Symbols.folder, description: "Folder")
            if folder.id == selected { folderPicker.select(folderPicker.lastItem) }
        }
        if folderPicker.numberOfItems == 0 { folderPicker.addItem(withTitle: "No folders added") }
        statusLabel.stringValue = store == nil ? "Shared storage unavailable — check app signing" :
            (FIFinderSyncController.isExtensionEnabled ? (FinderRenamer.isEnabled ? "Finder extension and filename editing are enabled" : "Enable Filename Editing to finish setup") : "Enable Alright in Finder Extension Settings")
    }
    func applicationDidBecomeActive(_ notification: Notification) { refreshStatus() }
    @objc private func enableFilenameEditing(_ sender: Any?) {
        FinderRenamer.requestAccess()
        NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility")!)
    }
    @objc private func manageExtension(_ sender: Any?) { FIFinderSyncController.showExtensionManagementInterface() }
    private func showError(_ error: Error) {
        showMainWindow(nil)
        let alert = NSAlert()
        alert.messageText = "Document creation could not finish"
        alert.informativeText = error.localizedDescription
        alert.beginSheetModal(for: window!)
    }
    @objc private func addFolder(_ sender: Any?) {
        guard let store else { return }
        let panel = NSOpenPanel()
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = true
        panel.prompt = "Allow Folder"
        panel.message = "Allow Alright to create documents inside the selected folders and their subfolders."
        guard panel.runModal() == .OK else { return }
        do { for url in panel.urls { try store.add(url) } } catch { showError(error) }
        refreshStatus()
    }
    @objc private func removeFolder(_ sender: Any?) {
        guard let id = folderPicker.selectedItem?.representedObject as? String else { return }
        do { try store?.remove(id: id) } catch { showError(error) }
        refreshStatus()
    }
    @objc private func revealFolder(_ sender: Any?) {
        guard let store, let folder = store.folders.first(where: { $0.id == folderPicker.selectedItem?.representedObject as? String }) else { return }
        do {
            let url = try store.resolve(folder)
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            NSWorkspace.shared.open(url)
        } catch { showError(error) }
    }
    func application(_ application: NSApplication, open urls: [URL]) {
        receivedFinderRequest = true
        prepareStore()
        guard let store else { showError(AlrightError(message: "Shared storage unavailable. Check app signing.")); return }
        // Finish one create → rename sequence before accepting another.
        let previous = creationTask
        creationTask = Task { @MainActor [weak self] in
            await previous?.value
            for url in urls {
                do {
                    guard FinderRenamer.isEnabled else {
                        FinderRenamer.requestAccess()
                        throw AlrightError(message: "Enable Filename Editing in macOS Settings, then choose a document from Finder again.")
                    }
                    let file = try DocumentService(store: store).create(requestURL: url)
                    try await FinderRenamer().begin(file)
                    self?.resultLabel.stringValue = "Created \(file.lastPathComponent)"
                } catch { self?.showError(error) }
            }
        }
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag { showMainWindow(nil) }
        return true
    }
}
