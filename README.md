# resolve-cut

Cut video end to end in DaVinci Resolve from footage in iCloud Drive: scan the sources,
write a cut plan, build the timeline with markers, and render.

This is an English fork of [joeseesun/qiaomu-cut-skill](https://github.com/joeseesun/qiaomu-cut-skill)
(MIT, Copyright © 向阳乔木). The upstream project is a larger Chinese-language video-direction
pipeline built on ffmpeg and ListenHub. This fork keeps the idea of an agent-driven, verifiable cut
workflow and replaces the render and source stack with DaVinci Resolve.

## What it does

- Scans iCloud Drive (or any folder) for video, and flags iCloud placeholders that are not downloaded.
- Builds a Resolve project and timeline from a JSON edit list (`in`/`out` seconds per clip).
- Places markers at each clip's real timeline position.
- Renders with a Resolve preset and reports the job status.

## Requirements

- macOS with DaVinci Resolve Studio (tested on 21.1.0.14)
- Python 3 (standard library only)
- For the standalone route: Resolve preferences → System → General → External scripting using = Local
- For the MCP route: DaVinci Resolve MCP server
- iCloud Photos needs an export or Full Disk Access. See [references/icloud-sources.md](references/icloud-sources.md).

## Quick start

```bash
python3 scripts/scan_icloud.py "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Downloads"
cp examples/cut-plan.example.json plan.json   # edit sources, in/out, output
python3 scripts/resolve_cut.py plan.json --dry-run
python3 scripts/resolve_cut.py plan.json       # Resolve must be running
```

## Files

| Path | Purpose |
|---|---|
| `SKILL.md` | Skill instructions (agent-facing) |
| `scripts/scan_icloud.py` | Read-only scanner for source folders |
| `scripts/resolve_cut.py` | Plan validation, timeline build, marker placement, render |
| `examples/cut-plan.example.json` | Two-clip example plan |
| `references/icloud-sources.md` | iCloud Drive vs Photos access |
| `references/resolve-api-notes.md` | Verified Resolve API calls and limits |
| `references/reels-editing.md` | Reels structure, cut technique, captions, safe zones |
| `references/sound-engineering.md` | Loudness targets, ducking, mix order, Resolve audio |
| `references/editing-styles.md` | Talking head, vlog, cinematic, documentary, meme, beat-synced |
| `scripts/master_audio.py` | Narration/music mix with ducking and −14 LUFS mastering (ffmpeg) |
| `tools/apple-analyze/` | On-device Apple Vision/SoundAnalysis shot analysis (Swift) |

## Known limits

- A 24 fps timeline with 25 or 30 fps sources shortens cuts by about 0.1 s per clip. Match `fps` to the source.
- One video track, no titles, captions, transitions, or audio mix yet.

## License

MIT. See [LICENSE](LICENSE). Original work © 向阳乔木; modifications © the fork maintainer.
