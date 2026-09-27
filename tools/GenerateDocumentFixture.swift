import Foundation

@main struct GenerateDocumentFixture {
    static func main() throws {
        let args = CommandLine.arguments
        guard args.count == 6, let kind = DocumentKind(rawValue: args[1]), let width = Int(args[2]), let height = Int(args[3]) else {
            fatalError("Usage: GenerateDocumentFixture <document-kind> <width> <height> <templates> <output>")
        }
        let content = try kind.contents(templates: URL(fileURLWithPath: args[4]), canvas: CanvasSize(width: width, height: height))
        try content.write(to: URL(fileURLWithPath: args[5]), options: .withoutOverwriting)
    }
}
