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
- Live end-to-end auth test: rip one YouTube + one Instagram item with real
  cookies loaded, confirm files land. (Pipeline verified with a public video;
  authenticated path not yet user-verified.)

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
