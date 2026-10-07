// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "OllamaMonitor",
    platforms: [.macOS("26.0")],
    products: [
        .executable(name: "OllamaMonitor", targets: ["OllamaMonitor"])
    ],
    targets: [
        .executableTarget(
            name: "OllamaMonitor",
            path: "Sources/OllamaMonitor"
        ),
        .testTarget(
            name: "OllamaMonitorTests",
            dependencies: ["OllamaMonitor"],
            path: "Tests/OllamaMonitorTests"
        )
    ]
)
