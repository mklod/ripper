# Ripper -- Changelog

## TODO
> [!tip] Queued for next build
> - (empty)

## Build 2026-06-05--0149

### Changes
- Formalized the project at `L:\PROJECTS\ripper` (canonical source + docs, git repo).
- Relocated runtime state (config + merged cookies temp) from the script dir to
  `%LOCALAPPDATA%\Ripper`; merged cookies are session secrets and the source copy
  is on a guest-readable share. Existing config migrated.
- Added README.md, install.ps1, requirements.txt, .gitignore, WORKPLAN.md, _status.md.

> [!warning] Testing Checklist
> - [ ] `install.ps1` runs clean on a fresh-ish machine (deps install, shortcut appears, app launches)
>   - Notes: not yet run on a second machine
> - [x] App launches from the deployed local copy and writes config to `%LOCALAPPDATA%\Ripper`
>   - Notes: verified 2026-06-05
> - [x] Merged cookies temp file is created under `%LOCALAPPDATA%\Ripper`, not the NAS
>   - Notes: verified 2026-06-05
> - [x] Live auth test: YouTube + Instagram with real cookies -> files land
>   - Notes: verified by user 2026-06-05 with live authenticated rips

## Build 2026-05-27--1700

### Changes
- Multi-file cookie support: Add/Remove list; 2+ files merged at rip time so
  Instagram + YouTube cookies work simultaneously.
- Removed the browser-cookie dropdown (Chrome locks its cookie DB; unreliable).
- Right-click Cut/Copy/Paste/Select-all on the links box and Save-to field.
- Quality toggle: best (default) vs forced 1080p H.264 MP4; read fresh each Rip.
  Strict no-re-encode (remux only); errors if no H.264 MP4 stream exists.

## Build 2026-05-21 (initial)

### Changes
- Initial app: yt-dlp + gallery-dl routing, batch link box, output folder,
  live log, cancel button, settings persistence.
- Installed gallery-dl; upgraded yt-dlp to nightly (PyPI stable was broken vs YouTube).
- Custom download-arrow icon (multi-res .ico) + desktop shortcut via pythonw.
