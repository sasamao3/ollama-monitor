import AppKit
import SwiftUI

struct WindowConfigurator: NSViewRepresentable {
    @ObservedObject var preferences: AppPreferences

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeNSView(context: Context) -> WindowTrackingView {
        let view = WindowTrackingView()
        view.onWindowChange = { [weak coordinator = context.coordinator] window in
            guard let window else { return }
            coordinator?.configure(window, preferences: preferences)
        }
        return view
    }

    func updateNSView(_ view: WindowTrackingView, context: Context) {
        view.onWindowChange = { [weak coordinator = context.coordinator] window in
            guard let window else { return }
            coordinator?.configure(window, preferences: preferences)
        }
        if let window = view.window {
            context.coordinator.configure(window, preferences: preferences)
        }
    }

    @MainActor
    final class Coordinator {
        private weak var configuredWindow: NSWindow?

        func configure(_ window: NSWindow, preferences: AppPreferences) {
            if configuredWindow !== window {
                configuredWindow = window
                preferences.restoreWindowFrameIfNeeded(window)
            }
            preferences.applyWindowPreferences(to: window)
        }
    }
}

final class WindowTrackingView: NSView {
    var onWindowChange: ((NSWindow?) -> Void)?

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        DispatchQueue.main.async { [weak self] in
            self?.onWindowChange?(self?.window)
        }
    }
}
