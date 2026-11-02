// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "Petal",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(name: "Petal"),
    ]
)
