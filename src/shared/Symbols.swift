import AppKit

@MainActor enum Symbols {
    static let newText = "doc.badge.plus"
    static let settings = "gearshape"
    static let addFolder = "folder.badge.plus"
    static let remove = "minus.circle"
    static let folder = "folder"
    static let all = [newText, settings, addFolder, remove, folder]
    static func image(_ name: String, description: String) -> NSImage? {
        NSImage(systemSymbolName: name, accessibilityDescription: description)
    }
}
