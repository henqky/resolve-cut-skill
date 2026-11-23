#!/usr/bin/env python3
"""Mix narration and music under a video, duck the music, and master to -14 LUFS.

Usage:
  python3 master_audio.py --video cut.mov --out final.mp4 \
      [--narration vo.wav] [--narration-delay 0.4] \
      [--music bed.mp3] [--duck-db -12] \
      [--target -14] [--true-peak -1]

- Video track is copied (no re-encode of pictures unless --reencode-video is given).
- The program audio is the video's own audio (kept) plus narration plus music.
- Music is ducked under narration with sidechain compression (narration is the key).
- The whole mix is normalized with two-pass ffmpeg loudnorm: measure, then apply
  linearly with the measured values. Target defaults to -14 LUFS, -1 dBTP.

Requires ffmpeg on PATH. Standard library only.
"""

import argparse
import json
import re
import subprocess
import sys


def run(cmd, capture=False):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}):\n{proc.stderr[-1500:]}")
    return proc.stderr if capture else ""


def video_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def build_graph(args, measured=None):
    """Return (filter_complex, extra_inputs) for the audio chain."""
    inputs = []
    parts = []
    mix_labels = []
    # Input 0 is the video; its own audio is the program bed.
    parts.append("[0:a]aresample=48000[prog]")
    mix_labels.append("[prog]")
    idx = 1
    if args.narration:
        inputs += ["-i", args.narration]
        delay_ms = int(round(args.narration_delay * 1000))
        narr_chain = f"[{idx}:a]aresample=48000,adelay={delay_ms}|{delay_ms},volume=1.2,apad"
        idx += 1
        if args.music:
            # The narration is needed twice: as the ducking key and in the mix.
            parts.append(narr_chain + ",asplit=2[narr_key][narr_mix]")
            mix_labels.append("[narr_mix]")
            inputs += ["-i", args.music]
            gain = 10 ** (args.music_gain_db / 20)
            parts.append(f"[{idx}:a]aresample=48000,volume={gain:.4f}[mus0]")
            # Duck the music while the narration key is present.
            parts.append("[mus0][narr_key]sidechaincompress=threshold=0.03:ratio=8:"
                         "attack=20:release=350:level_sc=1[mus]")
            mix_labels.append("[mus]")
            idx += 1
        else:
            parts.append(narr_chain + "[narr_mix]")
            mix_labels.append("[narr_mix]")
    elif args.music:
        inputs += ["-i", args.music]
        gain = 10 ** (args.music_gain_db / 20)
        parts.append(f"[{idx}:a]aresample=48000,volume={gain:.4f}[mus]")
        mix_labels.append("[mus]")
        idx += 1
    n = len(mix_labels)
    parts.append("".join(mix_labels) + f"amix=inputs={n}:duration=longest:normalize=0[mix]")


    if measured is None:
        chain = "[mix]loudnorm=I={t}:TP={p}:LRA=11:print_format=json[ln]".format(
            t=args.target, p=args.true_peak)
    else:
        chain = ("[mix]loudnorm=I={t}:TP={p}:LRA=11:measured_I={mi}:measured_TP={mtp}:"
                 "measured_LRA={mlra}:measured_thresh={mth}:offset={off}:linear=true[ln]").format(
            t=args.target, p=args.true_peak, mi=measured["input_i"], mtp=measured["input_tp"],
            mlra=measured["input_lra"], mth=measured["input_thresh"], off=measured["target_offset"])
    parts.append(chain)
    # Final true-peak guard AFTER loudnorm: loudnorm's gain can push peaks back over the ceiling.
    # 0.5 dB headroom: the limiter's release lets peaks overshoot its ceiling slightly.
    ceiling = 10 ** ((args.true_peak - 0.5) / 20)
    parts.append(f"[ln]alimiter=limit={ceiling:.4f}:attack=5:release=50:level=disabled[aout]")
    return ";".join(parts), inputs


def measure(args):
    fc, extra = build_graph(args, measured=None)
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", args.video, *extra,
           "-filter_complex", fc, "-map", "[aout]", "-vn", "-t", f"{video_duration(args.video):.3f}",
           "-f", "null", "-"]
    err = run(cmd, capture=True)
    m = re.search(r"\{\s*\"input_i\".*?\}", err, re.S)
    if not m:
        raise RuntimeError("loudnorm measurement not found in ffmpeg output")
    return json.loads(m.group(0))


def master(args):
    measured = measure(args)
    print("measured:", {k: measured[k] for k in ("input_i", "input_tp", "input_lra")}, file=sys.stderr)
    fc, extra = build_graph(args, measured=measured)
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", args.video, *extra,
           "-filter_complex", fc, "-map", "0:v", "-map", "[aout]",
           "-t", f"{video_duration(args.video):.3f}"]
    if args.reencode_video:
        cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p"]
    else:
        cmd += ["-c:v", "copy"]
    cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", args.out]
    run(cmd)
    print(f"wrote {args.out}", file=sys.stderr)


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--video", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--narration")
    p.add_argument("--narration-delay", type=float, default=0.0, help="seconds before narration starts")
    p.add_argument("--music")
    p.add_argument("--music-gain-db", type=float, default=-14.0, help="music level before ducking")
    p.add_argument("--duck-db", type=float, default=-12.0, help="informational; ducking uses sidechain ratio")
    p.add_argument("--target", type=float, default=-14.0, help="integrated loudness, LUFS")
    p.add_argument("--true-peak", type=float, default=-1.0, help="true peak ceiling, dBTP")
    p.add_argument("--reencode-video", action="store_true")
    args = p.parse_args(argv[1:])
    master(args)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
