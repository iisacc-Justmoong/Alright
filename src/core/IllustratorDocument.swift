import Foundation

/// A blank PDF-compatible AI with Illustrator's own native editing stream.
/// Only the two known artboard records in the bundled blank template are resized.
enum IllustratorDocument {
    static func contents(size: CanvasSize, templates: URL) throws -> Data {
        try size.validate()
        func resized(_ data: Data, native: Bool) throws -> Data {
            var result = data
            let replacements = [("%AI3_Cropmarks: 0 -1080 1920 0", "%AI3_Cropmarks: 0 -\(size.height) \(size.width) 0")]
                + (native ? [("%_1920 -1080 /RealPointRelToROrigin", "%_\(size.width) -\(size.height) /RealPointRelToROrigin")] : [])
            for (before, after) in replacements {
                let needle = Data(before.utf8)
                guard let range = result.range(of: needle), result.range(of: needle, in: range.upperBound..<result.count) == nil else {
                    throw AlrightError(message: "The Illustrator template has an unexpected artboard structure.")
                }
                result.replaceSubrange(range, with: Data(after.utf8))
            }
            return result
        }
        let metadata = try resized(Data(contentsOf: templates.appendingPathComponent("Blank.aimetadata")), native: false)
        let native = try resized(Data(contentsOf: templates.appendingPathComponent("Blank.aiprivate")), native: true)
        let chunks = stride(from: 0, to: native.count, by: 65536).map { Data(native[$0..<min($0 + 65536, native.count)]) }
        func stream(_ data: Data) -> Data { Data("<< /Length \(data.count) >>\nstream\n".utf8) + data + Data("\nendstream".utf8) }
        let box = "[0 0 \(size.width) \(size.height)]"
        var objects: [Data] = [
            Data("<< /Type /Catalog /Pages 2 0 R >>".utf8),
            Data("<< /Type /Pages /Count 1 /Kids [3 0 R] >>".utf8),
            Data("<< /Type /Page /Parent 2 0 R /MediaBox \(box) /CropBox \(box) /TrimBox \(box) /BleedBox \(box) /Resources << >> /Contents 4 0 R /PieceInfo << /Illustrator 5 0 R >> >>".utf8),
            stream(Data()),
            Data("<< /LastModified (D:20260925000000Z) /Private 6 0 R >>".utf8)
        ]
        let references = chunks.indices.map { "/AIPrivateData\($0 + 1) \($0 + 8) 0 R" }.joined(separator: " ")
        objects.append(Data("<< /AIMetaData 7 0 R \(references) /ContainerVersion 12 /CreatorVersion 30 /NumBlock \(chunks.count) /RoundtripVersion 24 >>".utf8))
        objects.append(stream(metadata))
        objects.append(contentsOf: chunks.map(stream))
        var pdf = Data("%PDF-1.6\n".utf8)
        var offsets = [0]
        for (index, object) in objects.enumerated() {
            offsets.append(pdf.count)
            pdf += Data("\(index + 1) 0 obj\n".utf8) + object + Data("\nendobj\n".utf8)
        }
        let xref = pdf.count
        pdf += Data("xref\n0 \(offsets.count)\n0000000000 65535 f \n".utf8)
        for offset in offsets.dropFirst() { pdf += Data(String(format: "%010d 00000 n \n", offset).utf8) }
        pdf += Data("trailer\n<< /Size \(offsets.count) /Root 1 0 R >>\nstartxref\n\(xref)\n%%EOF\n".utf8)
        return pdf
    }
}
