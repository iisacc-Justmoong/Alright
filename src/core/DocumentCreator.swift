import Foundation
import Darwin

struct AlrightError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

/// Document semantics stay here; filesystem ownership belongs to iiFileProvider.
enum DocumentCreator {
    static func create(root: String, relative: String, kind: DocumentKind = .text, content: Data = Data()) throws -> URL {
        try IisaccFileProvider.createDocument(root: root, relative: relative,
            title: kind.title, fileExtension: kind.fileExtension, content: content)
    }
}
