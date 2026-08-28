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

### Known trade-off (flagged to user)
HEVC output is **larger than the AV1 source** (110 MB → 169 MB, ~1.5x) — that's
inherent to AV1→HEVC. `\\murkyserver\murky4` is at **93% (1.7 TB free)**, so
heavy 4K ripping will eat into that. Tunable via `HEVC_CQ` in `ripper.pyw`.

### Next
- Watch the first few real 4K rips for size/time in practice.
- `--cookies-from-browser firefox` still deferred (unchanged).
