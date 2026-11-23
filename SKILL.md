---
name: resolve-cut
description: |
  Cut a video end to end in DaVinci Resolve from footage in iCloud Drive (or any local folder):
  scan sources, plan the cut as a JSON edit list, build a Resolve timeline with markers,
  and render the result. Use when the user asks to edit, cut, assemble, or render a video
  with DaVinci Resolve, or to make a rough cut from their iCloud footage. Drives Resolve through
  the DaVinci Resolve MCP (run_script / run_script_unsafe) or the external scripting module.
metadata:
  version: 0.1.0
  based_on: joeseesun/qiaomu-cut-skill (MIT)
---

# Resolve Cut

Turn a list of source clips into a rendered Resolve timeline. The skill does four things:

1. **Find footage**: scan iCloud Drive (or a folder) for video files, and flag iCloud placeholders
   that are not downloaded yet.
2. **Plan**: write a cut plan (`plan.json`): sources, in/out points in seconds, markers, output.
3. **Build**: create or reuse a Resolve project and timeline, import media, place subclips, add markers.
4. **Render**: queue and run a render job, then report the output file and job status.

## Preconditions

- DaVinci Resolve (Studio) is installed. The MCP can start it with `launch_resolve`.
- For the standalone route: Resolve preferences → System → General → External scripting using = **Local**.
- macOS must allow the terminal/host app to read the source folder. See [references/icloud-sources.md](references/icloud-sources.md).
  The Photos library is blocked by default and must be exported or granted Full Disk Access first.

## Workflow

### 1. Scan sources

```bash
python3 scripts/scan_icloud.py "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Downloads"
```

Each row has `status`: `local` (ready) or `not-downloaded` (open it in Finder or iCloud Drive first).
Never use a `not-downloaded` path in a plan.

### 2. Write the plan

Copy `examples/cut-plan.example.json` and edit it. Fields:

| Field | Meaning |
|---|---|
| `project`, `timeline` | Resolve project name (created or reused) and new timeline name. Use a new timeline name for each run. |
| `fps`, `width`, `height` | Timeline frame rate and size. Match `fps` to the dominant source rate (see Gotchas). |
| `output_dir`, `output_name` | Where the render goes. |
| `render_preset` | Optional Resolve preset name, e.g. `H.264 Master`, `YouTube - 1080p`, `ProRes 422 HQ`. |
| `clips[].source` | Absolute path to the file. |
| `clips[].in`, `clips[].out` | Seconds into the source. Must satisfy `0 <= in < out`. |
| `clips[].marker`, `marker_color`, `marker_note` | Optional marker placed at that clip's start on the timeline. |

Dry-run the plan first. It validates paths and ranges without touching Resolve:

```bash
python3 scripts/resolve_cut.py plan.json --dry-run
```

### 3. Build and render

Standalone (Resolve must be running):

```bash
python3 scripts/resolve_cut.py plan.json
```

Through the DaVinci Resolve MCP (no shell access to Resolve's Python):

1. `get_resolve_status`; if not running, `launch_resolve`.
2. `run_script_unsafe` with:
   ```python
   import json
   ns = {"resolve": resolve}
   exec(open("/ABS/PATH/scripts/resolve_cut.py").read(), ns)
   plan = json.load(open("/ABS/PATH/plan.json"))
   result = ns["build_and_render"](resolve, plan)
   ```
   Use `run_script` only for read-only checks. Its sandbox blocks file access.

The result reports `ok`, `job_status`, `timeline_frames`, `markers_added`, and the output name.

### 4. Verify

- `ok: true` and `JobStatus: Complete`.
- `timeline_frames` ≈ sum of `(out - in) × fps` (small differences are expected, see Gotchas).
- Check the file with `ffprobe` or by playing it. Confirm the cut points and marker positions match the plan.

## Gotchas (all verified on Resolve 21.1)

- **Source frame rates differ from the project.** Subclip frames are counted at each source's own rate,
  so the script converts seconds with the source FPS. Even so, when a 25 or 30 fps clip sits on a 24 fps
  timeline, Resolve's frame placement shortens the cut by about 0.1 s per clip. For exact durations, set
  `fps` to the source rate, or transcode the sources first.
- **End frame is exclusive.** `endFrame` in `CreateTimelineFromClips` must be `out × fps`, not `out × fps − 1`.
  With the inclusive reading, every clip came out one frame short (71 instead of 72 frames for 3 s).
- **Timeline start is 01:00:00:00.** Resolve's absolute frame numbers start at 86400 at 24 fps. The script
  places markers relative to the timeline start, so you don't need to handle this yourself.
- **Marker frames are timeline-relative.** They are computed from each item's real start, not from the plan math.
- **Re-using a timeline name** may create a second timeline. Pick a new `timeline` name per run.
- **Rendering is blocking.** The script waits up to `render_timeout_sec` (default 900 s).
- **No deletion.** The script never deletes media, projects, or timelines.

## Out of scope for this version

- Titles, captions, transitions, color grading, audio mix. Add them in Resolve, or extend `build_and_render`.
- Pulling from the Photos library directly (see the reference doc for the export route).
- Multi-track edits. The plan builds one video track, in order.
