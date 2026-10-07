import Foundation
import Combine

@MainActor
final class MonitorViewModel: ObservableObject {
    @Published private(set) var models: [RunningModel] = []
    @Published private(set) var lmStudioModels: [LMStudioRunningModel] = []
    @Published var selectedModelName: String?
    @Published var selectedLMStudioModelID: LMStudioRunningModel.ID?
    @Published private(set) var gpuUsage: Int?
    @Published private(set) var gpuMemoryInUseBytes: UInt64?
    @Published private(set) var gpuMemoryAllocatedBytes: UInt64?
    @Published private(set) var lastSync: Date?
    @Published private(set) var statusMessage = "Initializing..."
    @Published private(set) var lmStudioStatusMessage = "Checking server..."
    @Published private(set) var isConnected = false
    @Published private(set) var isLMStudioConnected = false
    @Published private(set) var isStoppingModel = false
    @Published private(set) var isStoppingLMStudioModel = false

    private let client = OllamaClient()
    private let lmStudioClient = LMStudioClient()
    private var pollingTask: Task<Void, Never>?

    func start() {
        guard pollingTask == nil else { return }
        pollingTask = Task { [weak self] in
            while !Task.isCancelled {
                await self?.refresh()
                do {
                    try await Task.sleep(for: .seconds(1))
                } catch {
                    break
                }
            }
        }
    }

    func stopSelectedModel() async {
        guard let modelName = selectedModelName, !isStoppingModel else { return }
        isStoppingModel = true
        defer { isStoppingModel = false }

        do {
            try await client.stop(model: modelName)
            await refresh()
            statusMessage = "Stop requested for \(modelName)"
        } catch {
            statusMessage = error.localizedDescription
        }
    }

    func stopSelectedLMStudioModel() async {
        guard let modelID = selectedLMStudioModelID,
              let model = lmStudioModels.first(where: { $0.id == modelID }),
              !isStoppingLMStudioModel else {
            return
        }

        isStoppingLMStudioModel = true
        defer { isStoppingLMStudioModel = false }

        do {
            try await lmStudioClient.unload(instanceID: model.instanceID)
            await refresh()
            lmStudioStatusMessage = "Stop requested for \(model.displayName)"
        } catch {
            lmStudioStatusMessage = error.localizedDescription
        }
    }

    private func refresh() async {
        async let modelResult = fetchModels()
        async let lmStudioResult = fetchLMStudioModels()
        async let gpuResult = Task.detached(priority: .utility) {
            GPUUsageReader.read()
        }.value

        let (result, lmStudioResultValue, gpuSnapshot) = await (modelResult, lmStudioResult, gpuResult)
        gpuUsage = gpuSnapshot?.utilizationPercent
        gpuMemoryInUseBytes = gpuSnapshot?.memoryInUseBytes
        gpuMemoryAllocatedBytes = gpuSnapshot?.memoryAllocatedBytes
        lastSync = Date()

        if let fetchedModels = result.models {
            models = fetchedModels
            isConnected = true
            statusMessage = fetchedModels.isEmpty
                ? "No models currently running"
                : "Ready"
            if selectedModelName.map({ name in fetchedModels.contains(where: { $0.name == name }) }) != true {
                selectedModelName = fetchedModels.first?.name
            }
        } else {
            models = []
            selectedModelName = nil
            isConnected = false
            statusMessage = result.error ?? "Ollama server unavailable"
        }

        if let fetchedModels = lmStudioResultValue.models {
            lmStudioModels = fetchedModels
            isLMStudioConnected = true
            lmStudioStatusMessage = fetchedModels.isEmpty ? "No models currently loaded" : "Ready"
            if selectedLMStudioModelID.map({ id in fetchedModels.contains(where: { $0.id == id }) }) != true {
                selectedLMStudioModelID = fetchedModels.first?.id
            }
        } else {
            lmStudioModels = []
            selectedLMStudioModelID = nil
            isLMStudioConnected = false
            lmStudioStatusMessage = lmStudioResultValue.error ?? "Bionic Local API server unavailable"
        }
    }

    private func fetchModels() async -> (models: [RunningModel]?, error: String?) {
        do {
            return (try await client.runningModels(), nil)
        } catch {
            return (nil, error.localizedDescription)
        }
    }

    private func fetchLMStudioModels() async -> (models: [LMStudioRunningModel]?, error: String?) {
        do {
            return (try await lmStudioClient.runningModels(), nil)
        } catch {
            return (nil, error.localizedDescription)
        }
    }
}
