import AppKit
@preconcurrency import ApplicationServices

@MainActor struct FinderRenamer {
    static var isEnabled: Bool { AXIsProcessTrusted() }
    static func requestAccess() {
        _ = AXIsProcessTrustedWithOptions([kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary)
    }
    private func value(_ element: AXUIElement, _ name: String) -> CFTypeRef? {
        var result: CFTypeRef?
        guard AXUIElementCopyAttributeValue(element, name as CFString, &result) == .success else { return nil }
        return result
    }
    private func children(_ element: AXUIElement) -> [AXUIElement] {
        value(element, kAXChildrenAttribute) as? [AXUIElement] ?? []
    }
    private func elements(_ element: AXUIElement, depth: Int = 0) -> [AXUIElement] {
        guard depth < 12 else { return [] }
        return [element] + children(element).prefix(300).flatMap { elements($0, depth: depth + 1) }
    }
    private func contains(_ file: URL, in element: AXUIElement) -> Bool {
        elements(element).contains {
            guard let url = value($0, kAXURLAttribute) as? URL else { return false }
            return url.standardizedFileURL == file.standardizedFileURL
        }
    }
    private func selectedOnly(_ file: URL, window: AXUIElement) -> Bool {
        for element in elements(window) {
            for attribute in [kAXSelectedRowsAttribute, kAXSelectedChildrenAttribute] {
                if let selected = value(element, attribute) as? [AXUIElement], selected.count == 1, contains(file, in: selected[0]) { return true }
            }
        }
        return false
    }
    func begin(_ file: URL) async throws {
        guard Self.isEnabled else {
            throw AlrightError(message: "Enable Alright in System Settings → Privacy & Security → Accessibility (Device Control and Data Access) to enter filenames in Finder.")
        }
        NSWorkspace.shared.activateFileViewerSelecting([file])
        guard let finder = NSRunningApplication.runningApplications(withBundleIdentifier: "com.apple.finder").first else {
            throw AlrightError(message: "Finder is unavailable. The file was created at \(file.path).")
        }
        let app = AXUIElementCreateApplication(finder.processIdentifier)
        AXUIElementSetMessagingTimeout(app, 0.25)
        for _ in 0..<40 {
            try await Task.sleep(for: .milliseconds(100))
            guard NSWorkspace.shared.frontmostApplication?.processIdentifier == finder.processIdentifier,
                  let rawWindow = value(app, kAXFocusedWindowAttribute), CFGetTypeID(rawWindow) == AXUIElementGetTypeID() else { continue }
            let window = unsafeDowncast(rawWindow, to: AXUIElement.self)
            guard selectedOnly(file, window: window),
                  let rawBar = value(app, kAXMenuBarAttribute), CFGetTypeID(rawBar) == AXUIElementGetTypeID() else { continue }
            let bar = unsafeDowncast(rawBar, to: AXUIElement.self)
            let names = ["Rename", "이름 변경", "名前を変更", "Renommer", "Umbenennen", "Renombrar", "Rinomina", "重命名", "重新命名"]
            guard let rename = elements(bar).first(where: { names.contains(value($0, kAXTitleAttribute) as? String ?? "") && value($0, kAXEnabledAttribute) as? Bool == true }) else { continue }
            // Invoke Finder's own command only after verifying the single selected file URL.
            guard AXUIElementPerformAction(rename, kAXPressAction as CFString) == .success else { continue }
            for _ in 0..<20 {
                try await Task.sleep(for: .milliseconds(50))
                if let rawFocus = value(app, kAXFocusedUIElementAttribute), CFGetTypeID(rawFocus) == AXUIElementGetTypeID() {
                    let focus = unsafeDowncast(rawFocus, to: AXUIElement.self)
                    let text = value(focus, kAXValueAttribute) as? String
                    if value(focus, kAXRoleAttribute) as? String == kAXTextFieldRole,
                       text == file.lastPathComponent || text == file.deletingPathExtension().lastPathComponent {
                        return // Finder selects the stem and preserves the extension itself.
                    }
                }
            }
            break // Never toggle rename a second time or send a blind Return key.
        }
        throw AlrightError(message: "Created \(file.lastPathComponent), but Finder did not enter filename editing. Select the file and press Return.")
    }
}
