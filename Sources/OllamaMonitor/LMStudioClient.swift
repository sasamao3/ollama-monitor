import Foundation

struct LMStudioRunningModel: Identifiable {
    let modelKey: String
    let displayName: String
    let type: String
    let sizeBytes: Int64
    let instanceID: String

    var id: String { "\(modelKey)::\(instanceID)" }
}

struct LMStudioModelsResponse: Decodable {
    let models: [LMStudioModelRecord]

    var loadedModels: [LMStudioRunningModel] {
        models.flatMap { model in
            (model.loadedInstances ?? []).map { instance in
                let instanceID = instance.id.flatMap { $0.isEmpty ? nil : $0 } ?? model.key
                return LMStudioRunningModel(
                    modelKey: model.key,
                    displayName: model.displayName ?? model.key,
                    type: model.type,
                    sizeBytes: model.sizeBytes ?? 0,
                    instanceID: instanceID
                )
            }
        }
    }
}

struct LMStudioModelRecord: Decodable {
    let type: String
    let key: String
    let displayName: String?
    let sizeBytes: Int64?
    let loadedInstances: [LMStudioLoadedInstance]?

    private enum CodingKeys: String, CodingKey {
        case type
        case key
        case displayName = "display_name"
        case sizeBytes = "size_bytes"
        case loadedInstances = "loaded_instances"
    }
}

struct LMStudioLoadedInstance: Decodable {
    let id: String?
}

enum LMStudioClientError: LocalizedError {
    case invalidURL
    case invalidResponse
    case serverNotRunning(port: Int)
    case serverUnavailable
    case server(statusCode: Int, detail: String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "The Bionic API URL is invalid."
        case .invalidResponse:
            return "Bionic returned an invalid model list."
        case let .serverNotRunning(port):
            return "Bionic Local API is off on port \(port). Enable it in Settings → Local Model API."
        case .serverUnavailable:
            return "Bionic Local API server unavailable. Enable it in Settings → Local Model API."
        case let .server(statusCode, detail):
            let message = detail.isEmpty ? "HTTP \(statusCode)" : detail
            return "Bionic API request failed: \(message)"
        }
    }
}

struct LMStudioClient {
    private let session: URLSession
    private let serverStatusReader = LMStudioServerStatusReader()

    init(session: URLSession = .shared) {
        self.session = session
    }

    func runningModels() async throws -> [LMStudioRunningModel] {
        let serverStatus = await serverStatusReader.current()
        let ports = candidatePorts(configuredPort: serverStatus?.port)

        var endpointError: LMStudioClientError?
        var connectionError: Error?
        for port in ports {
            do {
                return try await runningModels(port: port)
            } catch let error as LMStudioClientError {
                switch error {
                case let .server(statusCode, _) where statusCode == 404 || statusCode == 405:
                    endpointError = endpointError ?? error
                case .server:
                    throw error
                default:
                    connectionError = error
                }
            } catch {
                connectionError = error
            }
        }

        if let serverStatus, !serverStatus.running {
            throw LMStudioClientError.serverNotRunning(port: serverStatus.port)
        }
        if let endpointError {
            throw endpointError
        }
        if let connectionError {
            throw connectionError
        }
        throw LMStudioClientError.serverUnavailable
    }

    private func isConnectionRefused(_ error: Error) -> Bool {
        guard let urlError = error as? URLError else { return false }
        return [.cannotConnectToHost, .cannotFindHost, .dnsLookupFailed].contains(urlError.code)
    }

    func unload(instanceID: String) async throws {
        let serverStatus = await serverStatusReader.current()
        let ports = candidatePorts(configuredPort: serverStatus?.port)
        var endpointError: LMStudioClientError?
        var connectionError: Error?

        for port in ports {
            do {
                try await unload(instanceID: instanceID, port: port)
                return
            } catch let error as LMStudioClientError {
                switch error {
                case let .server(statusCode, _) where statusCode == 404 || statusCode == 405:
                    endpointError = endpointError ?? error
                case .server:
                    throw error
                default:
                    throw error
                }
            } catch {
                guard isConnectionRefused(error) else {
                    throw error
                }
                connectionError = error
            }
        }

        if let serverStatus, !serverStatus.running {
            throw LMStudioClientError.serverNotRunning(port: serverStatus.port)
        }
        if let endpointError {
            throw endpointError
        }
        if let connectionError {
            throw connectionError
        }
        throw LMStudioClientError.serverUnavailable
    }

    private func candidatePorts(configuredPort: Int?) -> [Int] {
        var ports: [Int] = []
        for port in [configuredPort, 1234, 8000].compactMap({ $0 }) where !ports.contains(port) {
            ports.append(port)
        }
        return ports
    }

    private func runningModels(port: Int) async throws -> [LMStudioRunningModel] {
        guard let url = URL(string: "http://localhost:\(port)/api/v1/models") else {
            throw LMStudioClientError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 1.5

        let (data, response) = try await session.data(for: request)
        guard let response = response as? HTTPURLResponse else {
            throw LMStudioClientError.invalidResponse
        }
        guard (200..<300).contains(response.statusCode) else {
            let detail = String(data: data, encoding: .utf8) ?? ""
            throw LMStudioClientError.server(statusCode: response.statusCode, detail: detail)
        }

        return try JSONDecoder().decode(LMStudioModelsResponse.self, from: data).loadedModels
    }

    private func unload(instanceID: String, port: Int) async throws {
        guard let url = URL(string: "http://localhost:\(port)/api/v1/models/unload") else {
            throw LMStudioClientError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 15
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(LMStudioUnloadRequest(instanceID: instanceID))

        let (data, response) = try await session.data(for: request)
        guard let response = response as? HTTPURLResponse else {
            throw LMStudioClientError.invalidResponse
        }
        guard (200..<300).contains(response.statusCode) else {
            let detail = String(data: data, encoding: .utf8) ?? ""
            throw LMStudioClientError.server(statusCode: response.statusCode, detail: detail)
        }
    }
}

private struct LMStudioUnloadRequest: Encodable {
    let instanceID: String

    private enum CodingKeys: String, CodingKey {
        case instanceID = "instance_id"
    }
}

private struct LMStudioServerStatus: Decodable, Sendable {
    let running: Bool
    let port: Int
}

private actor LMStudioServerStatusReader {
    private var cachedAt: Date?
    private var cachedStatus: LMStudioServerStatus?

    func current() async -> LMStudioServerStatus? {
        if let cachedAt, Date().timeIntervalSince(cachedAt) < 5 {
            return cachedStatus
        }

        let status = await Task.detached(priority: .utility) {
            Self.readStatus()
        }.value
        cachedAt = Date()
        cachedStatus = status
        return status
    }

    private nonisolated static func readStatus() -> LMStudioServerStatus? {
        let home = FileManager.default.homeDirectoryForCurrentUser
        let candidates = [
            home.appendingPathComponent(".lmstudio/bin/lms").path,
            "/opt/homebrew/bin/lms",
            "/usr/local/bin/lms"
        ]
        guard let executable = candidates.first(where: FileManager.default.isExecutableFile(atPath:)) else {
            return nil
        }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: executable)
        process.arguments = ["server", "status", "--json", "--quiet"]
        let output = Pipe()
        process.standardOutput = output
        process.standardError = FileHandle.nullDevice

        do {
            try process.run()
            let data = output.fileHandleForReading.readDataToEndOfFile()
            process.waitUntilExit()
            guard process.terminationStatus == 0,
                  let status = try? JSONDecoder().decode(LMStudioServerStatus.self, from: data),
                  (1...65535).contains(status.port) else {
                return nil
            }
            return status
        } catch {
            return nil
        }
    }
}
