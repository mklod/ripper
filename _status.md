# Ripper -- Status

## Current milestone
**v1 complete and formalized.** Working single-file Tkinter utility, deployed
locally, project home established on NAS with full docs.

## Last session (2026-06-05)
- Formalized the project at `L:\PROJECTS\ripper` (canonical source + docs).
- Decision: **run local, NAS is source** -- shortcut runs `C:\Users\mklod\Ripper`,
  NAS holds the authoritative copy + docs.
- Moved runtime state (config + merged cookies) out of the script dir into
  `%LOCALAPPDATA%\Ripper` -- the merged cookies file holds live session secrets
  and the NAS copy is guest-readable. Migrated existing config.
- Wrote README.md, install.ps1, requirements.txt, .gitignore, WORKPLAN.md,
  CHANGELOG.md. git init + first commit.

## Earlier sessions (2026-05)
- Built the app: yt-dlp + gallery-dl routing, batch links, live log, cancel.
- Added gallery-dl (was missing); upgraded yt-dlp to nightly.
- Custom download-arrow icon + desktop shortcut.
- Multi-file cookie support; dropped browser-cookie option (Chrome DB lock).
- Right-click Cut/Copy/Paste/Select-all on text fields.
- Quality toggle: best (default) vs forced 1080p H.264 MP4, never re-encodes.

## Next immediate task
- None outstanding. v1 verified end-to-end. Optional future work in WORKPLAN
  (per-collection subfolders, MP3 mode, concurrent downloads).

## Verification (2026-06-05)
- Live authenticated rips confirmed by user: YouTube + Instagram with real
  cookies.txt loaded -> files downloaded successfully. App is working in
  production use.

## Blockers
- None. Downloads require user-supplied `cookies.txt` (by design).

## Key decisions
- **Run local / NAS-source** over run-from-NAS: util must launch even if SMB is
  down (documented flakiness on this machine).
- **Runtime secrets in `%LOCALAPPDATA%`**, never beside the script (NAS is
  guest-readable LAN share).
- **No `--cookies-from-browser`**: Chrome locks its cookie DB + App-Bound
  Encryption makes it unreliable. `cookies.txt` only.
- **Never re-encode**: 1080p toggle selects pre-encoded H.264 streams and
  remuxes; no `--recode-video`. If no H.264 MP4 exists, the link errors.

## Sync note (two copies)
NAS `L:\PROJECTS\ripper` is authoritative. After editing there, redeploy local:
`Copy-Item L:\PROJECTS\ripper\ripper.pyw,L:\PROJECTS\ripper\ripper.ico C:\Users\mklod\Ripper\ -Force`
(or just re-run `install.ps1`).

## Maintenance (2026-06-16--0209) — YouTube broke; updated yt-dlp
- Symptom: YouTube rips failed — nsig extraction failed + "forcing SABR streaming"
  + "Only images are available" -> "Requested format is not available".
- Root cause: yt-dlp was 2025.05.22 (~13 months stale) vs YouTube's current player.
  (The stale-cookie warning was secondary — public videos work without cookies.)
- Fix: `python -m pip install -U yt-dlp gallery-dl` -> yt-dlp 2026.06.09,
  gallery-dl 1.32.3. Verified: watch?v=TXtqhP3aA9M downloaded (4K, 558MB webm), no cookies.
- Recurring issue: YouTube breaks yt-dlp periodically; fix is always `pip install -U yt-dlp`.
  Candidate: add the "Update deps" button from WORKPLAN so this is self-serve.

## Issue logged (2026-06-16) — YouTube bot-gate / cookie rotation
- Some YouTube videos are bot-gated: "Sign in to confirm you're not a bot" — they
  fail even with NO cookies (verified). They REQUIRE a valid signed-in session.
- Root pain: YouTube rotates session cookies whenever the logged-in browser loads
  a YouTube page, so a normally-exported cookies.txt goes stale fast ("cookies are
  no longer valid").
- Fix (works): re-export via INCOGNITO method — private window, log in, open a new
  tab to youtube.com/robots.txt, export, close the window immediately. Documented
  in README (Cookies section + troubleshooting row).
- Deferred (user: "drop it for now"): a `--cookies-from-browser firefox` option for
  always-fresh cookies. Logged in WORKPLAN possible-future.

## Session 2026-08-27--2340 — Kodi/Pi5 mode (webm problem solved properly)

### The ask
YouTube rips were landing as `.webm`. Goal set by user: **always grab best
quality** (explicitly *not* "cap at 1080p"), re-encode automatically when
needed for rpi5 playback, Instagram untouched, no duration gate.

### Root cause of the `.webm`
yt-dlp was already choosing an **MP4-container AV1** video stream. The file only
landed as `.webm` because it paired that with **Opus audio**, which ships in a
webm container. The extension was an audio-container artifact — the video pick
was never the problem.

### The hardware fact that drove the design (verified on the box)
The Pi 5's only hardware video decoder is `rpivid` (`/dev/video19`) and it
advertises exactly ONE coded format: **`S265` (HEVC)** — plus a 10-bit capture
format (`NC30`), so HDR/Main10 is covered. H.264/VP9/AV1 are all CPU-decoded;
`kodi.log` shows the V4L2 H.264 wrapper failing to open and handing off to
software on every play. YouTube never serves HEVC. **Therefore 4K on that box
is only possible via re-encode.**

### Shipped
- `ripper.pyw` — Kodi/Pi 5 mode, on by default. Best quality <=4K, AAC preferred
  at selection time (audio never re-encoded), output remuxed to MP4, then an
  HEVC re-encode **only** when needed.
- Rule keys on hardware, not codec name: keep HEVC (any res) and anything
  <=1080p; re-encode everything else. Catches 4K H.264 from non-YouTube sites
  too, which an "AV1/VP9 only" rule would have missed.
- HDR preserved (colour tags carried; Main10 for PQ/HLG).
- NVENC with libx265 fallback. Deployed to `C:\Users\mklod\Ripper`.

### Verification (all live, not assumed)
- Format sim: default best pick was `401+251` → `.webm`; with AAC preferred it's
  `401+140` → real `.mp4`, same video stream.
- End-to-end: 4K AV1 rip (110 MB) → HEVC Main 2160p MP4 (169 MB), AAC copied.
- **Live on the Pi:** copied that output to `murky4`, played via JSON-RPC —
  advanced **12.1 s of video in 12.0 s wall (1.01x)**, zero dropped frames,
  Kodi opened it via `DRMPRIME::Open - using decoder HEVC` with **no** "unable
  to open codec" fallback. Test file removed afterwards.
- Encoder benchmark (RTX 4070 SUPER, 4K30 AV1): presets p4..p7 all produced the
  SAME size (50.5 MB/20 s); p7 21.6 s vs p4 13.2 s → chose **p5** (~1.2x
  real-time). Decode is NOT the bottleneck (software AV1 ~187 fps), so
  `-hwaccel` was measured, made no difference, and was left out.

### 4K HDR verified (2026-08-28) — this is the quality ceiling being targeted
User's standard: "8k isn't real yet. 4kHDR == bestquality". Both halves checked:
- **Selection:** yt-dlp's default sort already prefers the HDR variant at a given
  resolution — two 4K HDR test videos both selected `dynamic_range=HDR10`
  (vp9.2 fmt 337 and av01 fmt 701). No format-selector change needed.
- **Survival through the re-encode:** ran the real pipeline on a 4K HDR10 rip.
  Source `vp9 Profile 2 / yuv420p10le / bt2020 / smpte2084 / bt2020nc` with
  mastering display metadata → output **`hevc Main 10`, identical pix_fmt and
  colour tags, mastering display metadata preserved**. Detection log line read
  `vp9 2160p HDR -> HEVC (hevc_nvenc)`.
- `rpivid` advertises a 10-bit capture format (`NC30`), so Main10 hardware-decodes
  on the Pi too.

### Correction to the size trade-off
Earlier note said HEVC output is larger than source. That's source-dependent, not
universal: the 4K AV1 clip grew 110 → 169 MB, but the 4K HDR VP9 clip **shrank
230 → 149 MB** (its source bitrate was much higher). Tunable via `HEVC_CQ`.

### Known trade-off (flagged to user)
HEVC output is **larger than the AV1 source** (110 MB → 169 MB, ~1.5x) — that's
inherent to AV1→HEVC. `\\murkyserver\murky4` is at **93% (1.7 TB free)**, so
heavy 4K ripping will eat into that. Tunable via `HEVC_CQ` in `ripper.pyw`.

### Next
- Watch the first few real 4K rips for size/time in practice.
- `--cookies-from-browser firefox` still deferred (unchanged).

## 2026-08-28 — published to GitHub
Repo pushed to **https://github.com/mklod/ripper** (public). Secret-scanned
before the first push: no credentials, keys or IPs in tracked files; exported
`cookies.txt` files are gitignored and runtime state lives in `%LOCALAPPDATA%`.

### Taskbar pin — confirmed current
The pinned shortcut targets `pythonw.exe "C:\Users\mklod\Ripper\ripper.pyw"`,
which is byte-identical (md5 `b8114912eeb2235874025a186f83d66d`) to the NAS
source. Deploying = copy `ripper.pyw` to `C:\Users\mklod\Ripper`; a running
instance must be restarted to pick up a new build.

## 2026-08-28--0015 — LIVE ON THE TV: 4K60 HDR verified end to end

Ripped LG's own 4K HDR demo (`bON-KPiiNCk`, AV1 HDR10 2160p60) with the real
app, Save-to pointed straight at the NAS Kodi folder — i.e. the actual workflow,
not a lab setup — then played it on the box.

- **Pipeline:** `av1 2160p HDR -> HEVC (hevc_nvenc)`. Output HEVC **Main 10**,
  3840x2160 @ 59.94, yuv420p10le, bt2020 / smpte2084 / bt2020nc, 272 MB.
- **Timing (SMB round trip included):** 102 s of 4K60 re-encoded in **112 s**
  (~0.9x real-time). Downloading and re-encoding directly to/from the NAS works
  fine — no need to stage locally.
- **Playback:** 1.00x (14.9 s of video in 15.0 s wall), zero dropped/skipped
  frames, opened via `DRMPRIME::Open - using decoder HEVC`.
- **HDR CONFIRMED BY THE USER ON THE TV** — LG showed its HDR badge.
- **And confirmed from the Pi side** via `modetest -M vc4 -c` on HDMI-A-1 while
  playing: `Colorspace = 10 (BT2020_YCC)`, `max bpc = 12`, and a populated
  `HDR_OUTPUT_METADATA` blob decoding to:
  eotf **2 = SMPTE ST 2084 (PQ)**, Rec.2020 primaries (0.708/0.292,
  0.170/0.797, 0.131/0.046), D65 white point, 1000-nit mastering display,
  MaxCLL 1000 / MaxFALL 280 — the source's own mastering metadata, carried
  through the re-encode and out over HDMI.

### Benign log line to ignore
`CDVDVideoCodecDRMPRIME::FilterOpen - avfilter_graph_config: Invalid argument
(-22)` appears on EVERY playback on this build (H.264, HEVC and AV1 alike,
including files that predate this work). Pre-existing, not caused by these rips.

### Left on the NAS
`LG 4K DEMO HDR 2018 (60FPS) ELBA [bON-KPiiNCk].mp4` is still in
`youtube rips - watch later` — it's a genuine 4K HDR demo, keep or bin it.

## 2026-10-02--1856 — real-run bug: vertical video needlessly re-encoded

User handed over `ripper log.txt` from a real 13-link run (The Streets, 4K
music videos + making-ofs). The pipeline worked — **12/13 ok**, the one failure
being an age-gated video (`0caDHap3Nf4`, "Sign in to confirm your age"), which
is expected: the only cookie file configured is `Dropbox/Reels/IG.txt`
(Instagram), no YouTube cookies loaded.

### The bug (found by reading the run, not by a test)
`SW_SAFE_HEIGHT = 1080` compared **height**, so a **1080x1920 vertical** video
was re-encoded — despite having *exactly* the same pixel count as 1080p
landscape (2,073,600) and decoding just as easily on the Pi. It cost a
generation of quality for nothing, which directly contradicts the "best
quality, re-encode only if necessary" rule.

**Fix:** compare **total pixels** against the 1080p landscape frame + 10% slack
(`SW_SAFE_PIXELS = int(1920*1080*1.1)` = 2,280,960). Re-checked all 12 files
from the run through the new rule — only the vertical one changes verdict:

| file | WxH | px | vs 1080p | old rule | new rule |
|---|---|---|---|---|---|
| BRAVE ST ANDREW - THE STREETS | 1080x1080 | 1,166,400 | 0.56x | keep | keep |
| BRAVE ST ANDREW (vertical) | 1080x1920 | 2,073,600 | 1.00x | **re-encode** | **keep** |
| End of the Queue | 1920x1440 | 2,764,800 | 1.33x | re-encode | re-encode |
| 3 Minutes to Midnight | 2160x2160 | 4,665,600 | 2.25x | re-encode | re-encode |
| Bright Sunny Day | 3840x2024 | 7,772,160 | 3.75x | re-encode | re-encode |
| Utopia / making-ofs | 3840x2160 | 8,294,400 | 4.00x | re-encode | re-encode |

Also: the log line now prints **real dimensions** (`vp9 1080x1920`) instead of
`vp9 1920p`, which misleadingly read as "above 1080p".

### Verified live
Ran a real 1080x1920 VP9 rip through `kodi_pass()`:
`vp9 1080x1920 - software-decodes fine, no re-encode` — byte-identical in and
out. Also re-ripped the affected video pristine (VP9 616 untouched, 33.6 MB)
and swapped it in for the old second-generation HEVC transcode (63.6 MB) — so
the file in `Downloads/the-streets` is now better quality AND half the size.

### Incidental findings (no code change needed)
- **Format 616 is YouTube's "Premium" 1080p tier** (5670k vs 1631k for standard
  VP9 248, 1196k for AV1 399) and is **HLS/m3u8 only**. The selector picking it
  is correct for "best quality" — don't add an https-only protocol preference,
  it would silently downgrade to a third of the bitrate.
- A transient **HTTP 403** hit the HLS fragments on one re-rip attempt; an
  immediate retry succeeded. Not a code fault — the same format had downloaded
  fine earlier in the day. A failed HLS run does leave an orphan `.fNNN.mp4`
  partial in the output folder (that's yt-dlp's resume behaviour, left alone).

### Next
- Age-gated videos need a YouTube `cookies.txt` (incognito-export method, see
  README). Only IG cookies are loaded right now.
- Still untested: Instagram path end-to-end, cancel-mid-re-encode.
