import AppKit

// Generate every standard ICNS representation directly from the system symbol.
@main struct GenerateIcon {
    @MainActor static func main() throws {
        let directory = URL(fileURLWithPath: CommandLine.arguments[1])
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        for size in [16, 32, 128, 256, 512] {
            for scale in [1, 2] {
                let pixels = size * scale
                let side = CGFloat(pixels)
                let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: pixels, pixelsHigh: pixels, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
                NSGraphicsContext.saveGraphicsState()
                NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
                let background = NSBezierPath(roundedRect: NSRect(x: side * 0.06, y: side * 0.06, width: side * 0.88, height: side * 0.88), xRadius: side * 0.20, yRadius: side * 0.20)
                NSGradient(starting: NSColor(srgbRed: 0.18, green: 0.49, blue: 0.98, alpha: 1), ending: NSColor(srgbRed: 0.16, green: 0.24, blue: 0.78, alpha: 1))!.draw(in: background, angle: -90)
                let config = NSImage.SymbolConfiguration(pointSize: side * 0.53, weight: .medium).applying(.init(paletteColors: [.white]))
                guard let symbol = NSImage(systemSymbolName: "doc.badge.plus", accessibilityDescription: "Alright")?.withSymbolConfiguration(config) else {
                    throw NSError(domain: "Alright.Icon", code: 1, userInfo: [NSLocalizedDescriptionKey: "Required SF Symbol is unavailable"])
                }
                let ratio = min(side * 0.56 / symbol.size.width, side * 0.60 / symbol.size.height)
                let target = NSSize(width: symbol.size.width * ratio, height: symbol.size.height * ratio)
                symbol.draw(in: NSRect(x: (side - target.width) / 2, y: (side - target.height) / 2, width: target.width, height: target.height))
                NSGraphicsContext.restoreGraphicsState()
                let suffix = scale == 2 ? "@2x" : ""
                try rep.representation(using: .png, properties: [:])!.write(to: directory.appendingPathComponent("icon_\(size)x\(size)\(suffix).png"))
            }
        }
    }
}
