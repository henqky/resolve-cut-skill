# apple-analyze

On-device shot analysis for a video, using only Apple frameworks (no network, no API key).

- **Vision** `VNClassifyImageRequest`: scene and object labels per sampled frame.
- **Vision** `VNDetectHumanRectanglesRequest`: people count per frame.
- **Vision** `VNRecognizeTextRequest`: on-screen text.
- **SoundAnalysis** `SNClassifySoundRequest`: top environmental audio classes across the clip.

Build and run (Xcode command-line tools required):

```bash
swiftc -O tools/apple-analyze/analyze.swift -o /tmp/apple-analyze
/tmp/apple-analyze clip.mp4 2 60 > analysis.json   # <video> <interval_s> [max_frames]
```

Limits: labels are generic ("machine", "document"), not shot descriptions. Use them to flag
people, text, and sound, and to group shots. Describe shots yourself from the sampled frames.
