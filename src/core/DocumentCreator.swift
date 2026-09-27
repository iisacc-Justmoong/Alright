import Foundation
import Darwin

struct AlrightError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

/// No-follow traversal and atomic exclusive publication preserve existing files.
enum DocumentCreator {
    static func create(root: String, relative: String, kind: DocumentKind = .text, content: Data = Data()) throws -> URL {
        let components = relative.split(separator: "/").map(String.init)
        guard root.hasPrefix("/"), !relative.hasPrefix("/"), !components.contains(".."),
              !root.contains("\0"), !relative.contains("\0") else {
            throw AlrightError(message: "A granted root and a safe relative directory are required.")
        }
        var directory = open(root, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
        guard directory >= 0 else { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO) }
        defer { close(directory) }
        for component in components where component != "." {
            let next = openat(directory, component, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC)
            guard next >= 0 else { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO) }
            close(directory)
            directory = next
        }
        // Publish only a complete document. The hidden staging name is never a final file.
        let temporary = ".alright-" + UUID().uuidString + ".tmp"
        let file = openat(directory, temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0o600)
        guard file >= 0 else { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO) }
        defer { close(file); unlinkat(directory, temporary, 0) }
        try content.withUnsafeBytes { bytes in
            var offset = 0
            while offset < bytes.count {
                let count = write(file, bytes.baseAddress!.advanced(by: offset), bytes.count - offset)
                if count < 0 && errno == EINTR { continue }
                guard count > 0 else { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO) }
                offset += count
            }
        }
        guard fchmod(file, 0o644) == 0, fsync(file) == 0 else {
            throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO)
        }
        for index in 1...10_000 {
            let suffix = index == 1 ? "" : " \(index)"
            let name = "\(kind.title)\(suffix).\(kind.fileExtension)"
            if renameatx_np(directory, temporary, directory, name, UInt32(RENAME_EXCL)) == 0 {
                return URL(fileURLWithPath: root).appendingPathComponent(relative).appendingPathComponent(name).standardizedFileURL
            }
            if errno != EEXIST { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO) }
        }
        throw AlrightError(message: "Too many files named \(kind.title) in this folder.")
    }
}
