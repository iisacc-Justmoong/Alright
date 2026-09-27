import Foundation

enum PhotoshopDocument {
    static func contents(size: CanvasSize) throws -> Data {
        try size.validate()
        func u16(_ value: UInt16) -> Data { var v = value.bigEndian; return withUnsafeBytes(of: &v) { Data($0) } }
        func u32(_ value: UInt32) -> Data { var v = value.bigEndian; return withUnsafeBytes(of: &v) { Data($0) } }
        func ascii(_ value: String) -> Data { Data(value.utf8) }
        func block(_ data: Data) -> Data { u32(UInt32(data.count)) + data }
        let width = size.width, height = size.height
        // PackBits also handles odd widths and runs shorter than 128 pixels.
        var row = Data()
        var remaining = width
        while remaining > 0 {
            let count = min(128, remaining)
            row.append(count == 1 ? 0 : UInt8(257 - count))
            row.append(0)
            remaining -= count
        }
        let counts = (0..<height).reduce(into: Data()) { data, _ in data += u16(UInt16(row.count)) }
        let pixels = (0..<height).reduce(into: Data()) { data, _ in data += row }
        let channel = u16(1) + counts + pixels
        var layer = u32(0) + u32(0) + u32(UInt32(height)) + u32(UInt32(width)) + u16(4)
        for id: UInt16 in [0, 1, 2, 65535] { layer += u16(id) + u32(UInt32(channel.count)) }
        layer += ascii("8BIMnorm") + Data([255, 0, 0, 0])
        let extra = u32(0) + u32(0) + Data([7]) + ascii("Layer 1")
        layer += block(extra)
        var layerInfo = u16(65535) + layer // Negative layer count identifies merged transparency.
        for _ in 0..<4 { layerInfo += channel }
        if layerInfo.count % 2 != 0 { layerInfo.append(0) }
        let layerMask = block(layerInfo) + u32(0)
        let resolution = u32(72 << 16) + u16(1) + u16(1) + u32(72 << 16) + u16(1) + u16(1)
        let resources = ascii("8BIM") + u16(1005) + u16(0) + block(resolution)
        var psd = ascii("8BPS") + u16(1) + Data(repeating: 0, count: 6) + u16(4)
        psd += u32(UInt32(height)) + u32(UInt32(width)) + u16(8) + u16(3)
        psd += u32(0) + block(resources) + block(layerMask) + u16(1)
        for _ in 0..<4 { psd += counts }
        for _ in 0..<4 { psd += pixels }
        return psd
    }
}
