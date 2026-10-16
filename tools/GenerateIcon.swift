import AppKit

// Generate standard ICNS representations from the Illustrator-exported master.
@main struct GenerateIcon {
    @MainActor static func main() throws {
        guard CommandLine.arguments.count == 3 else {
            throw NSError(domain: "Alright.Icon", code: 1, userInfo: [NSLocalizedDescriptionKey: "Usage: AlrightIconGenerator <1024px master.png> <output.iconset>"])
        }
        let source = URL(fileURLWithPath: CommandLine.arguments[1])
        let directory = URL(fileURLWithPath: CommandLine.arguments[2])
        let masterData = try Data(contentsOf: source)
        guard let master = NSBitmapImageRep(data: masterData),
              master.pixelsWide == 1024, master.pixelsHigh == 1024,
              let image = master.cgImage else {
            throw NSError(domain: "Alright.Icon", code: 2, userInfo: [NSLocalizedDescriptionKey: "The app icon master must be a readable 1024 × 1024 PNG"])
        }
        if master.hasAlpha {
            for y in 0..<1024 {
                for x in 0..<1024 where master.colorAt(x: x, y: y)?.alphaComponent != 1 {
                    throw NSError(domain: "Alright.Icon", code: 3, userInfo: [NSLocalizedDescriptionKey: "The app icon must fill the complete square with opaque artwork"])
                }
            }
        }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        for size in [16, 32, 128, 256, 512] {
            for scale in [1, 2] {
                let pixels = size * scale
                let suffix = scale == 2 ? "@2x" : ""
                let output = directory.appendingPathComponent("icon_\(size)x\(size)\(suffix).png")
                if pixels == 1024 {
                    try masterData.write(to: output)
                    continue
                }
                guard let context = CGContext(data: nil, width: pixels, height: pixels,
                                              bitsPerComponent: 8, bytesPerRow: pixels * 4,
                                              space: CGColorSpace(name: CGColorSpace.sRGB)!,
                                              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
                    throw NSError(domain: "Alright.Icon", code: 4, userInfo: [NSLocalizedDescriptionKey: "Unable to create the app icon bitmap"])
                }
                context.interpolationQuality = .high
                context.draw(image, in: CGRect(x: 0, y: 0, width: pixels, height: pixels))
                guard let resized = context.makeImage(),
                      let png = NSBitmapImageRep(cgImage: resized).representation(using: .png, properties: [:]) else {
                    throw NSError(domain: "Alright.Icon", code: 5, userInfo: [NSLocalizedDescriptionKey: "Unable to encode the app icon PNG"])
                }
                try png.write(to: output)
            }
        }
    }
}
