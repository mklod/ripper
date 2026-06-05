# Ripper -- Workplan

## Project Summary
A single-file Windows desktop utility (Python/Tkinter) to download videos and
image galleries from the web. Paste links, click Rip. Routes Instagram URLs to
gallery-dl and everything else to yt-dlp. Personal tool, no server, no telemetry.

## Tech Stack
- Python 3.12, Tkinter (stdlib GUI)
- Backends: yt-dlp (video), gallery-dl (Instagram images/galleries)
- ffmpeg (stream merge / remux only -- never transcode)
- Windows shortcut + PowerShell installer

## Key Files
| File | Purpose |
|------|---------|
| `ripper.pyw` | The entire app |
| `ripper.ico` | Download-arrow icon (multi-res 16-256px) |
| `install.ps1` | Deps + deploy + desktop shortcut |
| `requirements.txt` | yt-dlp, gallery-dl |
| `README.md` | Docs + install + cookies guide |

## Stages

### Stage 1 -- Core ripper -- COMPLETE
yt-dlp + gallery-dl routing, batch link input, live log, cancel, output folder,
desktop shortcut + icon.

### Stage 2 -- Auth + quality -- COMPLETE
Multi-file cookies.txt support (IG + YT simultaneously, merged at runtime),
dropped browser-cookie path, right-click clipboard menus, best/1080p-H.264
quality toggle with a strict no-re-encode guarantee.

### Stage 3 -- Formalization -- COMPLETE
NAS project home, runtime secrets relocated to %LOCALAPPDATA%, README +
installer + tracking docs, git repo.

### Stage 4 -- Verification -- TODO
Live authenticated end-to-end test (YouTube + Instagram with real cookies).

### Possible future -- TODO (not committed)
- Per-collection subfolder output so big IG collections don't dump flat.
- Optional MP3 audio-only mode for YouTube.
- Concurrent downloads (currently sequential).
- Auto-update deps button.
