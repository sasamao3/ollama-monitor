import Foundation

struct RunningModel: Decodable, Identifiable {
    let name: String
    let digest: String
    let size: Int64

    var id: String { name }

    private enum CodingKeys: String, CodingKey {
        case name
        case digest
        case size
    }

    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        name = try values.decode(String.self, forKey: .name)
        digest = try values.decodeIfPresent(String.self, forKey: .digest) ?? ""
        size = try values.decodeIfPresent(Int64.self, forKey: .size) ?? 0
    }
}

private struct RunningModelsResponse: Decodable {
    let models: [RunningModel]?
}

private struct StopModelRequest: Encodable {
    let model: String
    let keepAlive = 0

    private enum CodingKeys: String, CodingKey {
        case model
        case keepAlive = "keep_alive"
    }
}

enum OllamaClientError: LocalizedError {
    case invalidURL
    case invalidResponse
    case server(statusCode: Int, detail: String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "The Ollama API URL is invalid."
        case .invalidResponse:
            return "Ollama returned an invalid response."
        case let .server(statusCode, detail):
            let message = detail.isEmpty ? "HTTP \(statusCode)" : detail
            return "Ollama request failed: \(message)"
        }
    }
}

struct OllamaClient {
    private let apiBase = "http://localhost:11434/api"
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func runningModels() async throws -> [RunningModel] {
        let data = try await send(path: "ps", method: "GET", timeout: 2)
        return try JSONDecoder().decode(RunningModelsResponse.self, from: data).models ?? []
    }

    func stop(model: String) async throws {
        let body = try JSONEncoder().encode(StopModelRequest(model: model))
        _ = try await send(path: "generate", method: "POST", body: body, timeout: 5)
    }

    private func send(
        path: String,
        method: String,
        body: Data? = nil,
        timeout: TimeInterval
    ) async throws -> Data {
        guard let url = URL(string: "\(apiBase)/\(path)") else {
            throw OllamaClientError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = timeout
        request.httpBody = body
        if body != nil {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await session.data(for: request)
        guard let response = response as? HTTPURLResponse else {
            throw OllamaClientError.invalidResponse
        }
        guard (200..<300).contains(response.statusCode) else {
            let detail = String(data: data, encoding: .utf8) ?? ""
            throw OllamaClientError.server(statusCode: response.statusCode, detail: detail)
        }
        return data
    }
}
