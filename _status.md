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
