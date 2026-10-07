import Foundation

struct GPUUsageSnapshot: Sendable {
    let utilizationPercent: Int?
    let memoryInUseBytes: UInt64?
    let memoryAllocatedBytes: UInt64?
}

enum GPUUsageReader {
    static func read() -> GPUUsageSnapshot? {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/sbin/ioreg")
        process.arguments = ["-rw0", "-c", "IOAccelerator"]
        process.standardError = FileHandle.nullDevice

        let output = Pipe()
        process.standardOutput = output

        do {
            try process.run()
            let data = output.fileHandleForReading.readDataToEndOfFile()
            process.waitUntilExit()
            guard process.terminationStatus == 0,
                  let text = String(data: data, encoding: .utf8) else {
                return nil
            }

            let snapshot = GPUUsageSnapshot(
                utilizationPercent: integerValue(named: "Device Utilization %", in: text).map(Int.init),
                memoryInUseBytes: integerValue(named: "In use system memory", in: text),
                memoryAllocatedBytes: integerValue(named: "Alloc system memory", in: text)
            )
            guard snapshot.utilizationPercent != nil
                    || snapshot.memoryInUseBytes != nil
                    || snapshot.memoryAllocatedBytes != nil else {
                return nil
            }
            return snapshot
        } catch {
            return nil
        }
    }

    private static func integerValue(named key: String, in text: String) -> UInt64? {
        guard let keyRange = text.range(of: "\"\(key)\"=") else { return nil }
        let digits = text[keyRange.upperBound...].prefix(while: \.isNumber)
        return UInt64(digits)
    }
}
