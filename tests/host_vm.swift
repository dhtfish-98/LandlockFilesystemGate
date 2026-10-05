import Foundation
import Virtualization

@main
struct LandlockLabVM {
    static func main() async throws {
        guard CommandLine.arguments.count == 3 else {
            fputs("usage: host_vm <kernel-Image> <initramfs>\n", stderr)
            exit(2)
        }
        let configuration = VZVirtualMachineConfiguration()
        configuration.cpuCount = 2
        configuration.memorySize = 1024 * 1024 * 1024
        configuration.platform = VZGenericPlatformConfiguration()
        let loader = VZLinuxBootLoader(kernelURL: URL(fileURLWithPath: CommandLine.arguments[1]))
        loader.initialRamdiskURL = URL(fileURLWithPath: CommandLine.arguments[2])
        loader.commandLine = "console=hvc0 rdinit=/bin/sh panic=0"
        configuration.bootLoader = loader
        let console = VZVirtioConsoleDeviceSerialPortConfiguration()
        console.attachment = VZFileHandleSerialPortAttachment(
            fileHandleForReading: FileHandle.standardInput,
            fileHandleForWriting: FileHandle.standardOutput
        )
        configuration.serialPorts = [console]
        try configuration.validate()
        let vm = VZVirtualMachine(configuration: configuration)
        try await vm.start()
        while vm.state != .stopped {
            try await Task.sleep(for: .milliseconds(250))
        }
    }
}
