#!/usr/bin/env python3
"""List video files under a folder and flag iCloud placeholders.

iCloud Drive can keep files as `.NAME.icloud` stubs until they are downloaded.
Resolve cannot import a stub, so each one is reported with status "not-downloaded".

Usage: python3 scan_icloud.py [folder ...]   (default: iCloud Drive)
Stdlib only. Read-only: it never downloads or modifies files.
"""

import json
import os
import sys

DEFAULT_ROOT = os.path.expanduser("~/Library/Mobile Documents/com~apple~CloudDocs")
VIDEO_EXT = {".mov", ".mp4", ".m4v", ".mxf", ".mkv", ".avi", ".braw"}


def scan(roots):
    rows = []
    for root in roots:
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                stub = name.startswith(".") and name.endswith(".icloud")
                real = name[1:-len(".icloud")] if stub else name
                ext = os.path.splitext(real)[1].lower()
                if ext not in VIDEO_EXT:
                    continue
                path = os.path.join(dirpath, real if not stub else name)
                if stub:
                    rows.append({"path": os.path.join(dirpath, real), "status": "not-downloaded",
                                 "size": None})
                else:
                    rows.append({"path": path, "status": "local", "size": os.path.getsize(path)})
    return rows


def main(argv):
    roots = argv[1:] or [DEFAULT_ROOT]
    rows = scan(roots)
    print(json.dumps({"count": len(rows),
                      "not_downloaded": sum(r["status"] == "not-downloaded" for r in rows),
                      "files": rows}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
