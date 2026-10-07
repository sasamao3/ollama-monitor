import SwiftUI

struct ContentView: View {
    @ObservedObject var monitor: MonitorViewModel
    @ObservedObject var preferences: AppPreferences

    private let teal = Color(red: 0.01, green: 0.85, blue: 0.75)
    private let purple = Color(red: 0.73, green: 0.53, blue: 0.97)

    var body: some View {
        VStack(spacing: 20) {
            header

            HStack(alignment: .top, spacing: 18) {
                ollamaPanel
                lmStudioPanel
            }
            .frame(maxHeight: .infinity)

            footer
        }
        .padding(24)
        .background(Color(nsColor: .windowBackgroundColor))
        .preferredColorScheme(.dark)
    }

    private var header: some View {
        HStack(alignment: .center, spacing: 24) {
            VStack(alignment: .leading, spacing: 6) {
                Text("OLLAMA MONITOR")
                    .font(.system(size: 20, weight: .bold, design: .rounded))
                    .tracking(1.2)
                    .foregroundStyle(purple)
                Text(syncLabel)
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundStyle(.secondary)
            }

            Spacer(minLength: 12)

            gpuMeter
                .frame(width: 155)

            VStack(alignment: .trailing, spacing: 6) {
                Toggle("Always on Top", isOn: $preferences.alwaysOnTop)
                    .toggleStyle(.checkbox)
                    .font(.system(size: 12))
                HStack(spacing: 8) {
                    Text("Opacity")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                    Slider(value: $preferences.opacity, in: 0.2...1.0, step: 0.05)
                        .frame(width: 105)
                }
            }
        }
    }

    private var gpuMeter: some View {
        VStack(alignment: .trailing, spacing: 7) {
            Text(gpuLabel)
                .font(.system(size: 12, weight: .semibold, design: .monospaced))
                .foregroundStyle(gpuColor)
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.white.opacity(0.13))
                    if let usage = monitor.gpuUsage {
                        Capsule()
                            .fill(gpuColor)
                            .frame(width: geometry.size.width * CGFloat(min(max(usage, 0), 100)) / 100)
                    }
                }
            }
            .frame(height: 8)

            Text(gpuMemoryLabel)
                .font(.system(size: 9, weight: .medium, design: .monospaced))
                .foregroundStyle(.secondary)
                .help("GPU shared memory in use / allocated by the Apple GPU driver")
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.white.opacity(0.13))
                    if let fraction = gpuMemoryFraction {
                        Capsule()
                            .fill(teal.opacity(0.8))
                            .frame(width: geometry.size.width * fraction)
                    }
                }
            }
            .frame(height: 4)
        }
    }

    private var ollamaPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("OLLAMA")
                    .font(.system(size: 13, weight: .bold))
                    .tracking(0.8)
                    .foregroundStyle(teal)

                Spacer()

                Picker("Model", selection: $monitor.selectedModelName) {
                    ForEach(monitor.models) { model in
                        Text(model.name).tag(Optional(model.name))
                    }
                }
                .labelsHidden()
                .frame(maxWidth: 180)
                .disabled(monitor.models.isEmpty)

                Button {
                    Task { await monitor.stopSelectedModel() }
                } label: {
                    if monitor.isStoppingModel {
                        ProgressView().controlSize(.small)
                    } else {
                        Text("Stop")
                    }
                }
                .disabled(monitor.selectedModelName == nil || monitor.isStoppingModel)
            }

            if monitor.models.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: monitor.isConnected ? "cpu" : "network.slash")
                        .font(.system(size: 25))
                        .foregroundStyle(.secondary)
                    Text(monitor.isConnected ? "No models currently running." : "Ollama server unavailable.")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                    if !monitor.isConnected {
                        Text("Expected at localhost:11434")
                            .font(.system(size: 11))
                            .foregroundStyle(.tertiary)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Table(monitor.models) {
                    TableColumn("NAME") { model in
                        Text(model.name)
                            .font(.system(size: 12, design: .monospaced))
                    }
                    TableColumn("ID") { model in
                        Text(String(model.digest.prefix(12)))
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(.secondary)
                    }
                    TableColumn("SIZE") { model in
                        Text(sizeLabel(model.size))
                            .font(.system(size: 11, design: .monospaced))
                    }
                    TableColumn("STATUS") { _ in
                        Label("Running", systemImage: "circle.fill")
                            .labelStyle(.titleAndIcon)
                            .font(.system(size: 11))
                            .foregroundStyle(teal)
                    }
                }
                .tableStyle(.inset(alternatesRowBackgrounds: true))
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(panelBackground)
    }

    private var lmStudioPanel: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("BIONIC")
                    .font(.system(size: 13, weight: .bold))
                    .tracking(0.8)
                    .foregroundStyle(teal)
                Spacer()
                Button {
                    Task { await monitor.stopSelectedLMStudioModel() }
                } label: {
                    if monitor.isStoppingLMStudioModel {
                        ProgressView().controlSize(.small)
                    } else {
                        Text("Stop")
                    }
                }
                .disabled(monitor.selectedLMStudioModelID == nil || monitor.isStoppingLMStudioModel)
                .help("Unload the selected Bionic model from memory")
                Text(monitor.lmStudioStatusMessage)
                    .font(.system(size: 10))
                    .foregroundStyle(monitor.isLMStudioConnected ? teal : .secondary)
                    .lineLimit(1)
            }

            if !monitor.isLMStudioConnected {
                VStack(spacing: 8) {
                    Image(systemName: "network.slash")
                        .font(.system(size: 25))
                        .foregroundStyle(.secondary)
                    Text("Bionic Local API unavailable.")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                    Text("Enable Settings → Local Model API in Bionic")
                        .font(.system(size: 11))
                        .foregroundStyle(.tertiary)
                        .multilineTextAlignment(.center)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if monitor.lmStudioModels.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "cpu")
                        .font(.system(size: 25))
                        .foregroundStyle(.secondary)
                    Text("No models currently loaded.")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                Table(monitor.lmStudioModels, selection: $monitor.selectedLMStudioModelID) {
                    TableColumn("NAME") { model in
                        Text(model.displayName)
                            .font(.system(size: 12, design: .monospaced))
                            .lineLimit(1)
                    }
                    TableColumn("INSTANCE") { model in
                        Text(model.instanceID)
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                    TableColumn("SIZE") { model in
                        Text(sizeLabel(model.sizeBytes))
                            .font(.system(size: 11, design: .monospaced))
                    }
                    TableColumn("TYPE") { model in
                        Text(model.type.uppercased())
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(teal)
                    }
                }
                .tableStyle(.inset(alternatesRowBackgrounds: true))
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(panelBackground)
    }

    private var footer: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(monitor.isConnected ? teal : Color.orange)
                .frame(width: 7, height: 7)
            Text("Ollama: \(monitor.statusMessage)")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
                .lineLimit(1)
                .truncationMode(.tail)
            Circle()
                .fill(monitor.isLMStudioConnected ? teal : Color.orange)
                .frame(width: 7, height: 7)
            Text("Bionic: \(monitor.lmStudioStatusMessage)")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
                .lineLimit(1)
                .truncationMode(.tail)
            Spacer()
            Text("11434 · BIONIC API")
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(.tertiary)
        }
    }

    private var panelBackground: some View {
        RoundedRectangle(cornerRadius: 12)
            .fill(Color.white.opacity(0.045))
            .overlay {
                RoundedRectangle(cornerRadius: 12)
                    .stroke(Color.white.opacity(0.08), lineWidth: 1)
            }
    }

    private var syncLabel: String {
        guard let lastSync = monitor.lastSync else { return "Last Sync: Initializing…" }
        return "Last Sync: \(lastSync.formatted(date: .omitted, time: .standard))"
    }

    private var gpuLabel: String {
        guard let usage = monitor.gpuUsage else { return "GPU: --" }
        return "GPU: \(usage)%"
    }

    private var gpuColor: Color {
        guard let usage = monitor.gpuUsage else { return .secondary }
        if usage < 30 { return teal }
        if usage < 70 { return Color.orange }
        return Color(red: 0.9, green: 0.35, blue: 0.48)
    }

    private var gpuMemoryLabel: String {
        guard let inUse = monitor.gpuMemoryInUseBytes else { return "GPU MEM: --" }
        let inUseGB = Double(inUse) / 1_073_741_824
        guard let allocated = monitor.gpuMemoryAllocatedBytes else {
            return String(format: "GPU MEM: %.1f GB", inUseGB)
        }
        let allocatedGB = Double(allocated) / 1_073_741_824
        return String(format: "GPU MEM: %.1f / %.1f GB", inUseGB, allocatedGB)
    }

    private var gpuMemoryFraction: CGFloat? {
        guard let inUse = monitor.gpuMemoryInUseBytes,
              let allocated = monitor.gpuMemoryAllocatedBytes,
              allocated > 0 else {
            return nil
        }
        return min(CGFloat(inUse) / CGFloat(allocated), 1)
    }

    private func sizeLabel(_ bytes: Int64) -> String {
        guard bytes > 0 else { return "—" }
        return String(format: "%.1f GB", Double(bytes) / 1_073_741_824)
    }
}
