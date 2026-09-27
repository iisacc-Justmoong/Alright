import Foundation
import CoreGraphics

/// Stable identifiers are persisted in the host/extension request protocol.
enum DocumentKind: String, Codable, CaseIterable, Sendable {
    case text, markdown, richText, pdf, word, excel, powerpoint, openDocumentText, openDocumentSpreadsheet, openDocumentPresentation, json, csv, html, svg, photoshop, illustrator

    var title: String {
        switch self {
        case .text: "New Text"
        case .markdown: "New Markdown"
        case .richText: "New Rich Text"
        case .pdf: "New PDF"
        case .word: "New Word Document"
        case .excel: "New Excel Workbook"
        case .powerpoint: "New PowerPoint Presentation"
        case .openDocumentText: "New OpenDocument Text"
        case .openDocumentSpreadsheet: "New OpenDocument Spreadsheet"
        case .openDocumentPresentation: "New OpenDocument Presentation"
        case .json: "New JSON"
        case .csv: "New CSV"
        case .html: "New HTML"
        case .svg: "New SVG"
        case .photoshop: "New Photoshop Document"
        case .illustrator: "New Illustrator Document"
        }
    }
    var fileExtension: String {
        switch self {
        case .text: "txt"
        case .markdown: "md"
        case .richText: "rtf"
        case .pdf: "pdf"
        case .word: "docx"
        case .excel: "xlsx"
        case .powerpoint: "pptx"
        case .openDocumentText: "odt"
        case .openDocumentSpreadsheet: "ods"
        case .openDocumentPresentation: "odp"
        case .json: "json"
        case .csv: "csv"
        case .html: "html"
        case .svg: "svg"
        case .photoshop: "psd"
        case .illustrator: "ai"
        }
    }
    var menuTitle: String { "\(title) (.\(fileExtension))" }
    var symbol: String {
        switch self {
        case .text, .markdown, .richText: "doc.text"
        case .word, .openDocumentText: "doc.richtext"
        case .excel, .openDocumentSpreadsheet: "tablecells"
        case .powerpoint, .openDocumentPresentation: "rectangle.on.rectangle"
        case .pdf: "doc.richtext"
        case .json, .html: "chevron.left.forwardslash.chevron.right"
        case .csv: "tablecells"
        case .svg, .illustrator: "point.topleft.down.to.point.bottomright.curvepath"
        case .photoshop: "photo"
        }
    }
    func contents(templates: URL, canvas: CanvasSize = CanvasSize(width: 1920, height: 1080)) throws -> Data {
        switch self {
        case .text, .markdown, .csv: return Data()
        case .richText: return Data(#"{\rtf1\ansi\deff0{\fonttbl{\f0 Helvetica;}}\f0\fs24\pard\par}"#.utf8)
        case .json: return Data("{}\n".utf8)
        case .html: return Data("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<title>Untitled</title>\n</head>\n<body>\n</body>\n</html>\n".utf8)
        case .svg: return Data("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1920\" height=\"1080\" viewBox=\"0 0 1920 1080\"></svg>\n".utf8)
        case .pdf:
            let data = NSMutableData()
            var page = CGRect(x: 0, y: 0, width: 595.276, height: 841.89)
            guard let consumer = CGDataConsumer(data: data),
                  let context = CGContext(consumer: consumer, mediaBox: &page, nil) else {
                throw AlrightError(message: "Could not prepare a blank PDF.")
            }
            context.beginPDFPage(nil)
            context.endPDFPage()
            context.closePDF()
            return data as Data
        case .word, .excel, .powerpoint, .openDocumentText, .openDocumentSpreadsheet, .openDocumentPresentation:
            let data = try Data(contentsOf: templates.appendingPathComponent("Blank.\(fileExtension)"))
            guard data.count > 22, data.starts(with: [0x50, 0x4b, 0x03, 0x04]) else {
                throw AlrightError(message: "The bundled \(fileExtension.uppercased()) document is invalid. Reinstall Alright.")
            }
            return data
        case .photoshop: return try PhotoshopDocument.contents(size: canvas)
        case .illustrator: return try IllustratorDocument.contents(size: canvas, templates: templates)
        }
    }
}
