# iCloud Footage Sources

## iCloud Drive (works)

Path on macOS:

```
~/Library/Mobile Documents/com~apple~CloudDocs/
```

Verified: the terminal can list and read it, and Resolve can import from it directly
(tested with `.mp4` and `.MOV` files from `Downloads/`).

Files that are "Optimize Storage" stubs appear as `.NAME.icloud` and cannot be imported.
`scan_icloud.py` reports them as `not-downloaded`. Download them first (Finder → right-click → Download Now).

## iCloud Photos (blocked by default)

The Photos library is at `~/Pictures/Photos Library.photoslibrary`. On this machine, reading it from
the terminal fails with `Operation not permitted`, because macOS privacy controls block it.

Two routes, in order of preference:

1. **Export from Photos** (no permissions needed): select clips in Photos → File → Export → Export
   Unmodified Original. Save into an iCloud Drive folder, for example `iCloud Drive/Footage/`, and point
   the plan at that folder. Keep the export "Include" setting on originals.
2. **Grant Full Disk Access**: System Settings → Privacy & Security → Full Disk Access → enable the app
   that runs the script (Terminal, iTerm, or the host app that runs the MCP). Restart that app.
   Then scan `~/Pictures/Photos Library.photoslibrary/originals/`. Only use this if you accept reading the
   Photos internals. Photos may keep some videos "optimized" (not local) until originals are downloaded.

Never copy or modify files inside the Photos library directly.

## Other local folders

Any absolute path works. Run `scan_icloud.py <folder>` to check the folder.
