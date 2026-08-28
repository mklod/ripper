# Ripper -- Changelog

## TODO
> [!tip] Queued for next build
> - (empty)

## Build 2026-08-27--2340

### Changes
- **Kodi/Pi 5 mode (new, on by default).** yt-dlp rips now take the **best
  available quality up to 4K** and, if the result is something the Raspberry Pi 5
  can't hardware-decode, re-encode it to **HEVC MP4** so it plays smoothly in
  Kodi. Replaces the old "cap it at 1080p H.264" answer to the `.webm` problem.
- **The rule keys on the hardware, not the file extension:** keep anything HEVC
  (the Pi's only hardware-decoded codec) and anything <=1080p (CPU decode is
  comfortable there, and re-encoding it would only throw quality away);
  re-encode everything else. That covers 4K AV1/VP9 from YouTube *and* 4K H.264
  from other sites, which the Pi 5 also can't hardware-decode.
- **Instagram is untouched** -- gallery-dl rips never get probed or re-encoded,
  so reels keep ripping exactly as before.
- Default format selector is now best-<=4K with **AAC preferred at selection
  time**, so the audio track is never re-encoded, and output lands in MP4
  (`--merge-output-format mp4` + `--remux-video mp4`, which also catches
  single-file downloads that never hit the merger).
- HDR is preserved: colour primaries/transfer/matrix are carried across and the
  encode switches to Main10 when the source is PQ/HLG.
- Encoder is **NVENC when available**, falling back to libx265 on machines
  without an NVIDIA GPU.
- The old **Force 1080p H.264 MP4** toggle is kept as an escape hatch for
  maximum-compatibility devices (off by default).

### Why the `.webm` files were happening
yt-dlp was already picking an *MP4-container* AV1 video stream; the file only
landed as `.webm` because it paired it with Opus audio, which ships in a webm
container. The extension was an audio-container artifact, not a bad video pick.

> [!warning] Testing Checklist
> - [ ] Rip a 4K YouTube link -> log shows `av1 2160p -> HEVC (hevc_nvenc)...`, final file is `.mp4`
>   - Notes:
> - [ ] Rip a 1080p-max YouTube link -> log says "software-decodes fine, no re-encode", no transcode runs
>   - Notes:
> - [ ] Rip an Instagram reel -> gallery-dl path, no probe/re-encode line at all
>   - Notes:
> - [ ] Play a 4K rip on the Pi 5 in Kodi -> smooth, no stutter
>   - Notes:
> - [ ] Cancel mid-re-encode -> stops cleanly, original file left intact
>   - Notes:
> - [ ] Untick "Kodi/Pi 5 mode" -> best quality downloaded with no re-encode
>   - Notes:

## Build 2026-06-16--0220

### Changes
- **Maintenance:** updated yt-dlp 2025.05.22 -> 2026.06.09 + gallery-dl -> 1.32.3,
  fixing YouTube failures (nsig extraction / forced SABR / "only images available").
- **Update button:** "Update yt-dlp / gallery-dl" (bottom-right) streams
  `pip install -U yt-dlp gallery-dl` into the log and prints the new versions —
  self-serve fix for the recurring YouTube-breakage.
- **Rip/Cancel moved** to the right of the paste box (act right after pasting).
- **Copy log** button (copies the log to the clipboard).
- **Aligned** the Save-to entry and Cookie-files listbox (uniform label + button
  widths); **removed** the Open button next to Save to.

> [!warning] Testing Checklist
> - [ ] Rip a YouTube link end-to-end (best quality) -> file lands in Save-to
>   - Notes:
> - [ ] "Update yt-dlp / gallery-dl" runs, streams pip output, prints versions, re-enables
>   - Notes:
> - [ ] "Copy log" puts the log text on the clipboard
>   - Notes:
> - [ ] Save-to entry and Cookie-files box visibly line up; no Open button
>   - Notes:
> - [ ] Rip + Cancel sit beside the paste box; Cancel works mid-rip
>   - Notes:

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
