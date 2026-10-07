import SwiftUI

@main
@MainActor
struct OllamaMonitorApp: App {
    @StateObject private var monitor = MonitorViewModel()
    @StateObject private var preferences = AppPreferences.shared

    var body: some Scene {
        WindowGroup("Ollama Monitor + GPU") {
            ContentView(monitor: monitor, preferences: preferences)
                .frame(minWidth: 820, minHeight: 360)
                .background(WindowConfigurator(preferences: preferences).frame(width: 0, height: 0))
                .task {
                    monitor.start()
                }
        }
        .defaultSize(width: 1040, height: 700)
    }
}
