// Local, on-device shot analysis for a video using Apple frameworks only.
// Usage: analyze <video> <interval_seconds> [max_frames]
// Output: JSON with per-sample scene labels, people count, on-screen text, and audio classes.
import Foundation
import AVFoundation
import Vision
import SoundAnalysis
import CoreMedia

let args = CommandLine.arguments
guard args.count >= 3, let interval = Double(args[2]) else {
    FileHandle.standardError.write("usage: analyze <video> <interval_seconds> [max_frames]\n".data(using: .utf8)!)
    exit(2)
}
let maxFrames = args.count > 3 ? Int(args[3]) ?? 60 : 60
let url = URL(fileURLWithPath: args[1])
let asset = AVURLAsset(url: url)
let duration = CMTimeGetSeconds(asset.duration)

let gen = AVAssetImageGenerator(asset: asset)
gen.appliesPreferredTrackTransform = true
gen.requestedTimeToleranceBefore = .zero
gen.requestedTimeToleranceAfter = .zero

var frames: [(Double, CGImage)] = []
var t = 0.0
while t < duration && frames.count < maxFrames {
    if let img = try? gen.copyCGImage(at: CMTime(seconds: t, preferredTimescale: 600), actualTime: nil) {
        frames.append((t, img))
    }
    t += interval
}

var results: [[String: Any]] = []
for (time, img) in frames {
    let handler = VNImageRequestHandler(cgImage: img, options: [:])
    let classify = VNClassifyImageRequest()
    let people = VNDetectHumanRectanglesRequest()
    let text = VNRecognizeTextRequest()
    text.recognitionLevel = .fast
    text.usesLanguageCorrection = false
    try? handler.perform([classify, people, text])

    let labels = (classify.results ?? [])
        .filter { $0.confidence > 0.25 }
        .prefix(5)
        .map { ["label": $0.identifier, "confidence": Double(round($0.confidence * 100) / 100)] as [String: Any] }
    let personCount = (people.results ?? []).count
    let ocr = (text.results ?? []).compactMap { $0.topCandidates(1).first?.string }
    results.append([
        "time": time,
        "labels": Array(labels),
        "people": personCount,
        "on_screen_text": ocr,
    ])
}

// Audio: classify environmental sound with the built-in Apple classifier.
var audioClasses: [[String: Any]] = []
do {
    let analyzer = try SNAudioFileAnalyzer(url: url)
    let request = try SNClassifySoundRequest(classifierIdentifier: .version1)
    let observer = ClassifyObserver()
    try analyzer.add(request, withObserver: observer)
    analyzer.analyze()
    audioClasses = observer.summary()
} catch {
    audioClasses = [["error": "\(error)"]]
}

let out: [String: Any] = [
    "file": url.lastPathComponent,
    "duration": (duration * 100).rounded() / 100,
    "samples": results,
    "audio_top_classes": audioClasses,
]
let data = try JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted, .sortedKeys])
FileHandle.standardOutput.write(data)
print("")

final class ClassifyObserver: NSObject, SNResultsObserving {
    private var totals: [String: (sum: Double, n: Int)] = [:]
    private var windows = 0
    func request(_ request: SNRequest, didProduce result: SNResult) {
        guard let r = result as? SNClassificationResult else { return }
        windows += 1
        for c in r.classifications where c.confidence > 0.3 {
            let old = totals[c.identifier] ?? (0, 0)
            totals[c.identifier] = (old.sum + c.confidence, old.n + 1)
        }
    }
    func request(_ request: SNRequest, didFailWithError error: Error) {}
    func requestDidComplete(_ request: SNRequest) {}
    func summary() -> [[String: Any]] {
        totals.map { ["label": $0.key, "windows": $0.value.n,
                      "mean_confidence": Double(round($0.value.sum / Double($0.value.n) * 100) / 100)] as [String: Any] }
            .sorted { ($0["windows"] as! Int) > ($1["windows"] as! Int) }
            .prefix(10).map { $0 }
    }
}
