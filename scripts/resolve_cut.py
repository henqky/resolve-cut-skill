#!/usr/bin/env python3
"""Build a DaVinci Resolve timeline from a cut plan and render it.

Two ways to run it:

1. Standalone (uses Resolve's external scripting module):
       python3 resolve_cut.py path/to/plan.json [--dry-run]

   Requires DaVinci Resolve to be running with
   Preferences > System > General > External scripting using = Local.

2. Inside the DaVinci Resolve MCP (`run_script_unsafe`), where `resolve`
   is already injected: exec() this file, then call
       plan = json.load(open(path)); result = build_and_render(resolve, plan)

Cut plan format (see examples/cut-plan.example.json):

    {
      "project": "my-cut",            # Resolve project name (created or reused)
      "timeline": "main",             # timeline name
      "fps": 24,
      "width": 1080,
      "height": 1920,
      "output_dir": "/Users/you/Movies/my-cut",
      "output_name": "my-cut",
      "render_preset": "H.264 Master",  # optional, a Resolve preset name
      "clips": [
        {"source": "/abs/path/clip.mov", "in": 2.0, "out": 6.5,
         "marker": "hook", "marker_color": "Blue"}   # in/out are seconds
      ]
    }

The script never deletes media or projects. It only creates the named
project/timeline if missing and writes to output_dir.
"""

import json
import os
import sys
import time

RESOLVE_MODULES = (
    "/Library/Application Support/Blackmagic Design/"
    "DaVinci Resolve/Developer/Scripting/Modules/"
)


def validate_plan(plan):
    """Return a list of human-readable problems. Empty list means the plan is valid."""
    problems = []
    for key in ("project", "fps", "width", "height", "output_dir", "output_name", "clips"):
        if key not in plan:
            problems.append(f"missing key: {key}")
    if problems:
        return problems
    if not plan["clips"]:
        problems.append("clips is empty")
    for i, clip in enumerate(plan["clips"]):
        label = f"clips[{i}]"
        src = clip.get("source", "")
        if not os.path.isabs(src):
            problems.append(f"{label}.source must be an absolute path")
        elif not os.path.exists(src):
            problems.append(f"{label}.source not found (iCloud placeholder?): {src}")
        if "in" not in clip or "out" not in clip:
            problems.append(f"{label} needs both 'in' and 'out' (seconds)")
        elif not clip["out"] > clip["in"] >= 0:
            problems.append(f"{label}: need 0 <= in < out, got in={clip['in']} out={clip['out']}")
    return problems


def _media_by_path(media_pool, paths):
    """Import every path once and return {absolute_path: MediaPoolItem}."""
    wanted = set(paths)
    found = {}
    root = media_pool.GetRootFolder()
    # Import only files not already in the pool.
    for item in root.GetClipList() or []:
        p = item.GetClipProperty("File Path")
        if p in wanted:
            found[p] = item
    missing = [p for p in paths if p not in found]
    if missing:
        imported = media_pool.ImportMedia(missing) or []
        for item in imported:
            p = item.GetClipProperty("File Path")
            found[p] = item
    unresolved = [p for p in paths if p not in found]
    if unresolved:
        raise RuntimeError(f"Resolve could not import: {unresolved}")
    return found


def _open_or_create_project(resolve, name):
    pm = resolve.GetProjectManager()
    project = pm.LoadProject(name)
    if not project:
        project = pm.CreateProject(name)
    if not project:
        raise RuntimeError(f"Could not create or load project '{name}'")
    return project


def build_and_render(resolve, plan, dry_run=False):
    problems = validate_plan(plan)
    if problems:
        return {"ok": False, "problems": problems}
    if dry_run:
        total = sum(c["out"] - c["in"] for c in plan["clips"])
        return {"ok": True, "dry_run": True, "clips": len(plan["clips"]),
                "duration_sec": round(total, 3)}

    fps = plan["fps"]
    project = _open_or_create_project(resolve, plan["project"])
    project.SetSetting("timelineFrameRate", str(fps))
    project.SetSetting("timelineResolutionWidth", str(plan["width"]))
    project.SetSetting("timelineResolutionHeight", str(plan["height"]))

    media_pool = project.GetMediaPool()
    sources = sorted({c["source"] for c in plan["clips"]})
    media = _media_by_path(media_pool, sources)

    segments = []
    for clip in plan["clips"]:
        # Subclip frames are counted at the SOURCE frame rate, not the project rate.
        # (Mixing them shifts cuts and lengths when a source is 25 or 30 fps.)
        src_fps = float(media[clip["source"]].GetClipProperty("FPS") or fps)
        segments.append({
            "mediaPoolItem": media[clip["source"]],
            "startFrame": int(round(clip["in"] * src_fps)),
            "endFrame": int(round(clip["out"] * src_fps)) - 1,  # Resolve end frame is inclusive
        })
    timeline = media_pool.CreateTimelineFromClips(plan["timeline"], segments)
    if not timeline:
        raise RuntimeError("CreateTimelineFromClips returned no timeline")
    project.SetCurrentTimeline(timeline)

    # Place markers from where Resolve actually put each clip, not from our own math.
    items = timeline.GetItemListInTrack("video", 1) or []
    items.sort(key=lambda it: it.GetStart())
    markers_added = 0
    origin = timeline.GetStartFrame()
    for clip, item in zip(plan["clips"], items):
        if clip.get("marker"):
            ok = timeline.AddMarker(item.GetStart() - origin, clip.get("marker_color", "Blue"),
                                    clip["marker"], clip.get("marker_note", ""), 1)
            markers_added += 1 if ok else 0

    os.makedirs(plan["output_dir"], exist_ok=True)
    if plan.get("render_preset"):
        project.LoadRenderPreset(plan["render_preset"])
    project.SetRenderSettings({
        "SelectAllFrames": True,
        "TargetDir": plan["output_dir"],
        "CustomName": plan["output_name"],
        "ExportVideo": True,
        "ExportAudio": True,
    })
    job_id = project.AddRenderJob()
    project.StartRendering(job_id)

    deadline = time.time() + plan.get("render_timeout_sec", 900)
    while project.IsRenderingInProgress() and time.time() < deadline:
        time.sleep(1)
    status = project.GetRenderJobStatus(job_id)
    state = (status or {}).get("JobStatus")
    return {
        "ok": state == "Complete",
        "job_status": status,
        "timeline_frames": timeline.GetEndFrame() - timeline.GetStartFrame(),
        "markers_added": markers_added,
        "output_dir": plan["output_dir"],
        "output_name": plan["output_name"],
    }


def _connect_resolve():
    if RESOLVE_MODULES not in sys.path:
        sys.path.append(RESOLVE_MODULES)
    import DaVinciResolveScript as dvr  # provided by Resolve's installation
    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        raise RuntimeError("Could not reach DaVinci Resolve. Is it running with external scripting enabled?")
    return resolve


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        plan = json.load(fh)
    dry = "--dry-run" in argv
    if dry:
        result = build_and_render(None, plan, dry_run=True)
    else:
        result = build_and_render(_connect_resolve(), plan)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
