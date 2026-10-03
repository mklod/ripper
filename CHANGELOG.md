# Ripper -- Changelog

## TODO
> [!tip] Queued for next build
> - (empty)

## Build 2026-10-02--1856

### Changes
- **Fixed: vertical videos were being re-encoded for no reason.** The Kodi/Pi 5
  rule compared **height** against 1080, so a 1080x1920 vertical clip tripped it
  — even though it has *exactly* the same pixel count as 1080p landscape and
  decodes just as easily. It now compares **total pixels** against the 1080p
  landscape frame (plus 10% slack for odd dimensions), so vertical and square
  1080-class clips are left alone. Decode cost scales with pixels, not height.
- **Log now prints real dimensions** (`vp9 1080x1920`) instead of a height
  suffix (`vp9 1920p`), which read as "above 1080p" when it wasn't.

### Found by
A real 13-link run (`ripper log.txt`, 2026-10-02). 12/13 succeeded; of those,
11 were correctly re-encoded and one — a 1080x1920 vertical video — was
needlessly transcoded. Re-ripped it pristine afterwards.

> [!warning] Testing Checklist
> - [x] Vertical 1080x1920 rip -> log says "software-decodes fine, no re-encode", file untouched
>   - Notes: verified live — ran a real 1080x1920 VP9 rip through `kodi_pass()`, byte-identical in and out.
> - [x] Square 1080x1080 rip -> no re-encode
>   - Notes: verified against the real file in the run (1,166,400 px, well under budget).
> - [x] 1920x1440 / 2160x2160 / 3840x2160 -> still re-encoded
>   - Notes: re-checked all 12 files from the run through the new rule; only the vertical one changed verdict.
> - [ ] Rip an Instagram reel -> gallery-dl path, no probe/re-encode line at all
>   - Notes: still not run.
> - [ ] Cancel mid-re-encode -> stops cleanly, original file left intact
>   - Notes: still not tested.

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
- **4K HDR preserved end-to-end** (this is the quality ceiling being targeted):
  the format selector already prefers the HDR variant at a given resolution, and
  the re-encode carries it across -- verified on a real 4K HDR10 rip,
  vp9 Profile 2 / yuv420p10le / bt2020 / smpte2084 / bt2020nc + mastering
  display metadata in, **hevc Main 10 with all of it intact** out.
- Encoder is **NVENC when available**, falling back to libx265 on machines
  without an NVIDIA GPU.
- The old **Force 1080p H.264 MP4** toggle is kept as an escape hatch for
  maximum-compatibility devices (off by default).

### Why the `.webm` files were happening
yt-dlp was already picking an *MP4-container* AV1 video stream; the file only
landed as `.webm` because it paired it with Opus audio, which ships in a webm
container. The extension was an audio-container artifact, not a bad video pick.

> [!warning] Testing Checklist
> - [x] Rip a 4K YouTube link -> log shows `av1 2160p -> HEVC (hevc_nvenc)...`, final file is `.mp4`
>   - Notes: verified twice (4K30 AV1 SDR, 4K60 AV1 HDR). Output HEVC Main / Main 10 MP4.
> - [x] Rip a 4K **HDR** link -> log shows `... 2160p HDR -> HEVC`, and the TV switches into HDR on playback
>   - Notes: VERIFIED ON THE TV 2026-08-28. LG showed its HDR badge; user confirmed "got the HDR flag".
>     Confirmed from the Pi too: HDMI-A-1 `Colorspace=10 (BT2020_YCC)`, `max bpc=12`, and a populated
>     `HDR_OUTPUT_METADATA` blob decoding to eotf=2 (ST2084/PQ), Rec.2020 primaries, D65,
>     1000-nit mastering display, MaxCLL 1000 / MaxFALL 280 -- i.e. the source's own mastering
>     metadata, carried all the way through the re-encode and out over HDMI.
> - [x] Rip a 1080p-max YouTube link -> log says "software-decodes fine, no re-encode", no transcode runs
>   - Notes: decision path exercised against 6 real files in the Kodi folder (all h264 1080p/240p) --
>     every one correctly skipped. Not yet run as a live 1080p rip.
> - [ ] Rip an Instagram reel -> gallery-dl path, no probe/re-encode line at all
>   - Notes: not yet run. (Gated by `backend == "yt-dlp"`, so it can't fire, but untested live.)
> - [x] Play a 4K rip on the Pi 5 in Kodi -> smooth, no stutter
>   - Notes: 4K30 = 1.01x, 4K60 HDR = 1.00x, zero dropped/skipped frames, DRMPRIME hardware path.
> - [ ] Cancel mid-re-encode -> stops cleanly, original file left intact
>   - Notes: not yet tested.
> - [ ] Untick "Kodi/Pi 5 mode" -> best quality downloaded with no re-encode
>   - Notes: not yet tested.

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
