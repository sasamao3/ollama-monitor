import Foundation
import XCTest
@testable import OllamaMonitor

final class RunningModelTests: XCTestCase {
    func testDecodesOllamaProcessEntry() throws {
        let payload = Data(
            #"{"name":"llama3:latest","digest":"0123456789abcdef","size":1073741824}"#.utf8
        )

        let model = try JSONDecoder().decode(RunningModel.self, from: payload)

        XCTAssertEqual(model.name, "llama3:latest")
        XCTAssertEqual(model.id, "llama3:latest")
        XCTAssertEqual(model.digest, "0123456789abcdef")
        XCTAssertEqual(model.size, 1_073_741_824)
    }

    func testMissingOptionalFieldsUseSafeDefaults() throws {
        let payload = Data(#"{"name":"small-model"}"#.utf8)

        let model = try JSONDecoder().decode(RunningModel.self, from: payload)

        XCTAssertEqual(model.digest, "")
        XCTAssertEqual(model.size, 0)
    }
}

final class LMStudioModelsResponseTests: XCTestCase {
    func testOnlyLoadedInstancesArePresented() throws {
        let payload = Data(
            #"{"models":[{"type":"llm","key":"publisher/bionic","display_name":"Bionic","size_bytes":2147483648,"loaded_instances":[{"id":"bionic"}]},{"type":"llm","key":"unused-model","display_name":"Unused","size_bytes":1073741824,"loaded_instances":[]}]}"#.utf8
        )

        let response = try JSONDecoder().decode(LMStudioModelsResponse.self, from: payload)

        XCTAssertEqual(response.loadedModels.count, 1)
        XCTAssertEqual(response.loadedModels.first?.modelKey, "publisher/bionic")
        XCTAssertEqual(response.loadedModels.first?.displayName, "Bionic")
        XCTAssertEqual(response.loadedModels.first?.instanceID, "bionic")
        XCTAssertEqual(response.loadedModels.first?.sizeBytes, 2_147_483_648)
    }
}
