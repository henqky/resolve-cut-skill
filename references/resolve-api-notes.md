# DaVinci Resolve API Notes (verified on Resolve Studio 21.1.0.14)

Calls used by `scripts/resolve_cut.py`, and what each one was checked for.

| Call | Result observed |
|---|---|
| `resolve.GetProjectManager()`, `LoadProject(name)`, `CreateProject(name)` | Works. `LoadProject` returns falsy for missing names. |
| `project.SetSetting("timelineFrameRate" / "timelineResolutionWidth" / "...Height", str)` | Set before creating the timeline. |
| `mediaPool.ImportMedia([paths])` | Imports files from iCloud Drive directly. |
| `clip.GetClipProperty("File Path")`, `("FPS")`, `("Duration")` | Works. FPS returns a string such as `"25.0"`. |
| `mediaPool.CreateTimelineFromClips(name, [{mediaPoolItem, startFrame, endFrame}])` | Subclip frames are at the source's native rate. `endFrame` is inclusive. |
| `timeline.GetItemListInTrack("video", 1)`, `item.GetStart()`, `item.GetEnd()` | Real placement on the timeline. Timeline frames are absolute (start 86400 at 24 fps). |
| `timeline.AddMarker(frame, color, name, note, duration)` | Frame is timeline-relative. |
| `project.LoadRenderPreset(name)`, `SetRenderSettings({...})`, `AddRenderJob()`, `StartRendering(id)` | Render completes; output file written. |
| `project.IsRenderingInProgress()`, `GetRenderJobStatus(id)` | Returns `{"JobStatus": "Complete", "CompletionPercentage": 100, ...}`. |

## Sandbox limits (DaVinci Resolve MCP)

- `run_script`: sandboxed Python. No `os`, `sys`, `pathlib`, or file access. Good for read-only queries.
- `run_script_unsafe`: needed to read plan files, create output folders, and check output sizes.
- Both have a timeout (default 10 s, max 60 s for `run_script`). For renders, pass a longer `timeout`
  or run the script standalone.

## Frame-rate behaviour

A 25 fps clip placed on a 24 fps timeline gave 58 timeline frames for a 2.5 s cut, where 2.5 s at
24 fps would be 60. A 30 fps clip gave 59 frames for a 2.5 s cut. Set the project fps to match the
dominant source to avoid this.
