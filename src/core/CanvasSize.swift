import AppKit

struct CanvasSize: Codable, Equatable, Sendable {
    let width: Int
    let height: Int
    func validate() throws {
        guard (1...16383).contains(width), (1...16383).contains(height) else {
            throw AlrightError(message: "The screen dimensions are outside the supported document range (1–16383 pixels).")
        }
    }
    // Capture while the Finder menu is being built, before another app can change screens.
    static func atPointer() -> CanvasSize {
        let screen = NSScreen.screens.first { $0.frame.contains(NSEvent.mouseLocation) } ?? NSScreen.main ?? NSScreen.screens.first
        guard let screen else { return CanvasSize(width: 1920, height: 1080) }
        return CanvasSize(width: Int((screen.frame.width * screen.backingScaleFactor).rounded()),
                          height: Int((screen.frame.height * screen.backingScaleFactor).rounded()))
    }
}
