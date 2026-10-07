import AppKit
import Combine
import Foundation

private struct StoredConfiguration: Codable {
    var geometry: String?
    var topmost: Bool?
    var alpha: Double?
}

@MainActor
final class AppPreferences: ObservableObject {
    static let shared = AppPreferences()

    @Published var alwaysOnTop: Bool {
        didSet { save() }
    }

    @Published var opacity: Double {
        didSet { save() }
    }

    private let configurationURL: URL
    private var storedGeometry: String?

    private init() {
        configurationURL = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".ollama_monitor_config.json")

        var configuration: StoredConfiguration?
        if FileManager.default.fileExists(atPath: configurationURL.path) {
            do {
                let data = try Data(contentsOf: configurationURL)
                configuration = try JSONDecoder().decode(StoredConfiguration.self, from: data)
            } catch {
                NSLog("Unable to read Ollama Monitor settings: %@", error.localizedDescription)
                configuration = nil
            }
        } else {
            configuration = nil
        }

        storedGeometry = configuration?.geometry
        alwaysOnTop = configuration?.topmost ?? false
        let savedOpacity = configuration?.alpha ?? 1.0
        opacity = min(max(savedOpacity, 0.2), 1.0)
    }

    func restoreWindowFrameIfNeeded(_ window: NSWindow) {
        let frameName = "OllamaMonitorMainWindow"
        let restoredNativeFrame = window.setFrameUsingName(frameName)
        _ = window.setFrameAutosaveName(frameName)
        guard !restoredNativeFrame,
              let geometry = storedGeometry,
              let frame = legacyFrame(from: geometry) else {
            return
        }
        window.setFrame(frame, display: true)
    }

    func applyWindowPreferences(to window: NSWindow) {
        window.level = alwaysOnTop ? .floating : .normal
        window.alphaValue = opacity
        window.isOpaque = opacity >= 1.0
        window.backgroundColor = opacity >= 1.0 ? .windowBackgroundColor : .clear
    }

    private func save() {
        let configuration = StoredConfiguration(
            geometry: storedGeometry,
            topmost: alwaysOnTop,
            alpha: opacity
        )
        do {
            let data = try JSONEncoder().encode(configuration)
            try data.write(to: configurationURL, options: .atomic)
        } catch {
            NSLog("Unable to save Ollama Monitor settings: %@", error.localizedDescription)
        }
    }

    private func legacyFrame(from geometry: String) -> NSRect? {
        let pattern = #"^(\d+)x(\d+)(?:\+(\d+))?(?:\+(\d+))?$"#
        guard let expression = try? NSRegularExpression(pattern: pattern),
              let match = expression.firstMatch(
                in: geometry,
                range: NSRange(geometry.startIndex..., in: geometry)
              ),
              let width = integer(capture: 1, from: geometry, match: match),
              let height = integer(capture: 2, from: geometry, match: match),
              let screen = NSScreen.main ?? NSScreen.screens.first else {
            return nil
        }

        let x = integer(capture: 3, from: geometry, match: match) ?? 80
        let yFromTop = integer(capture: 4, from: geometry, match: match) ?? 80
        let visibleFrame = screen.visibleFrame
        let size = NSSize(width: max(width, 760), height: max(height, 520))
        var frame = NSRect(
            x: visibleFrame.minX + CGFloat(x),
            y: screen.frame.maxY - CGFloat(yFromTop) - size.height,
            width: size.width,
            height: size.height
        )
        frame.origin.x = min(max(frame.origin.x, visibleFrame.minX), max(visibleFrame.minX, visibleFrame.maxX - frame.width))
        frame.origin.y = min(max(frame.origin.y, visibleFrame.minY), max(visibleFrame.minY, visibleFrame.maxY - frame.height))
        return frame
    }

    private func integer(capture index: Int, from text: String, match: NSTextCheckingResult) -> Int? {
        guard index < match.numberOfRanges,
              let range = Range(match.range(at: index), in: text) else {
            return nil
        }
        return Int(text[range])
    }
}
