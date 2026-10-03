# Ripper

A one-click desktop utility for ripping videos and image galleries from the web.
Paste one or many links, click **Rip**. It auto-routes each URL to the right
backend:

- **Instagram** (`instagram.com`) -> [gallery-dl](https://github.com/mikf/gallery-dl)
  -- reels, photos, multi-image carousels, profiles, saved collections, stories.
- **Everything else** (YouTube, TikTok, X, Vimeo, ...) -> [yt-dlp](https://github.com/yt-dlp/yt-dlp).

Single-file Python/Tkinter GUI. No build step, no server, no telemetry.

![Ripper](ripper.ico)

---

## Features

- Paste a batch of links (one per line) and rip them in sequence.
- **Multi-file cookie support** -- load an Instagram `cookies.txt` *and* a
  YouTube `cookies.txt` at the same time; they're merged at rip time.
- **Kodi / Pi 5 mode** (on by default) -- takes the **best available quality up
  to 4K** and re-encodes to **HEVC MP4** only when the Raspberry Pi 5 couldn't
  hardware-decode the result. See [Kodi / Pi 5 mode](#kodi--pi-5-mode) below.
- **Force 1080p H.264 MP4** toggle (off by default) -- escape hatch for
  maximum-compatibility devices. Never re-encodes; remux only.
- Right-click Cut / Copy / Paste / Select-all on the text fields.
- Live download log, per-link progress, Cancel button.
- Remembers your output folder, cookie files, and quality toggle between runs.

---

## Requirements

- **Windows 10/11** (the launcher/installer scripts are Windows-specific; the
  Python app itself is cross-platform).
- **Python 3.10+** on PATH (developed on 3.12).
- **ffmpeg** on PATH (needed to merge separate video+audio streams).
- Python packages: **yt-dlp** and **gallery-dl**.

---

## Install (new machine / another user)

### Automated

From this project folder, in PowerShell:

```powershell
.\install.ps1
```

The script:
1. Verifies Python and ffmpeg are present (and tells you how to get them if not).
2. `pip install --upgrade yt-dlp gallery-dl`.
3. Copies `ripper.pyw` + `ripper.ico` to `%LOCALAPPDATA%\Programs\Ripper`.
4. Creates a Desktop shortcut ("Ripper") with the download-arrow icon, launched
   via `pythonw.exe` so no console window appears.

### Manual

1. Install Python 3.10+ (tick "Add to PATH") and ffmpeg (`winget install Gyan.FFmpeg`).
2. `pip install --upgrade yt-dlp gallery-dl`
3. Copy `ripper.pyw` and `ripper.ico` anywhere local (e.g. `C:\Users\<you>\Ripper`).
4. Make a shortcut whose target is:
   `<python>\pythonw.exe "<path>\ripper.pyw"` and set its icon to `ripper.ico`.

---

## Cookies -- the important part

Both YouTube and Instagram now **block most anonymous downloads** (you'll see
"Video unavailable" / "user could not be found"). The fix is to give Ripper your
logged-in session as a `cookies.txt` file.

`--cookies-from-browser` is intentionally **not** supported: on the dev machine
Chrome locks its cookie DB while running and its App-Bound Encryption blocks the
copy. Exported `cookies.txt` files are the reliable path.

**To export cookies:**
1. Install the Chrome/Firefox extension **"Get cookies.txt LOCALLY"**.
2. Log into YouTube (and/or Instagram) in the browser.
3. On the site, click the extension -> **Export** -> save e.g.
   `youtube_cookies.txt`, `instagram_cookies.txt`.
4. In Ripper, click **Add** under "Cookie files" and select them (you can add
   both). They persist between runs.

> Treat `cookies.txt` like a password -- it grants access to your logged-in
> account. Keep these files local; never put them on a shared drive.

### YouTube cookies rotate -- export them the right way

YouTube **rotates your session cookies every time the logged-in browser loads a
YouTube page**, so a normally-exported `cookies.txt` goes stale within
minutes/hours and you'll see *"The provided YouTube account cookies are no longer
valid"* and *"Sign in to confirm you're not a bot"*. Export from a **parked
private session** so the cookies never get rotated:

1. Open a **new Incognito / Private window** and **log into YouTube**.
2. Open a **new tab** and go to `https://www.youtube.com/robots.txt` (a static
   page -- stops YouTube from rotating the session).
3. Export with **"Get cookies.txt LOCALLY"** -> save over your YouTube cookies file.
4. **Close the Incognito window immediately** -- don't browse YouTube in it again.

Some videos are bot-gated and *require* a valid signed-in session (they fail even
with no cookies), so this is the only way to rip them.

> **Durable alternative (not implemented):** `--cookies-from-browser firefox`
> reads live, always-fresh cookies (Firefox doesn't lock its DB like Chrome).
> Deferred -- revisit if the manual re-export becomes a chore.

---

## Usage

1. Launch **Ripper** (desktop shortcut).
2. Paste links into the top box, one per line.
3. (Once) **Add** your cookie file(s).
4. Set **Save to** if you don't want the default `~\Downloads\Ripper`.
5. Tick **Force 1080p H.264 MP4** if you need maximum-compatibility files;
   otherwise leave it off for best quality.
6. Click **Rip**. Watch the log; use **Cancel** to stop after the current item.

### Instagram saved collections

Don't scrape tile URLs by hand -- Instagram virtualizes the grid, so most tiles
aren't in the page. Instead, open the collection and copy the **address-bar URL**:

```
https://www.instagram.com/<you>/saved/<collection-name>/17xxxxxxxxxxxxxxx/
```

Paste that single line into Ripper. gallery-dl's collection extractor walks the
entire collection via the API (handles pagination itself). Requires your
Instagram `cookies.txt`.

---

## Where things live

| What | Path |
|------|------|
| Canonical source + docs (this repo) | `L:\PROJECTS\ripper` (NAS) |
| Deployed/running copy | `C:\Users\mklod\Ripper` (local) |
| Runtime state (config, merged cookies temp) | `%LOCALAPPDATA%\Ripper` |
| Default download output | `%USERPROFILE%\Downloads\Ripper` |

Runtime state is deliberately kept in `%LOCALAPPDATA%`, never next to the script:
the merged cookies file contains live session secrets and the source copy lives
on a guest-readable network share.

---

## Architecture (one file)

`ripper.pyw` is a single Tkinter app:

- **URL routing** -- `is_instagram(url)` splits traffic between gallery-dl and yt-dlp.
- **`cookie_args()`** -- 0 files -> none; 1 file -> `--cookies <file>`; 2+ files
  -> concatenate into `%LOCALAPPDATA%\Ripper\_cookies_merged.txt` then
  `--cookies` that (Netscape cookie format is line-oriented, so domains coexist).
- **`build_cmd()`** -- assembles the backend command; adds the 1080p H.264 format
  selector + `--merge-output-format mp4` only when the toggle is on.
- **Worker thread** -- runs each link's child process, streams stdout into the
  log via a thread-safe queue; the UI stays responsive and Cancel can terminate
  the live process.

### Kodi / Pi 5 mode

The rips are aimed at a specific target: Kodi on a Raspberry Pi 5, reading from
the NAS. That box constrains what's worth downloading.

**The hardware fact everything follows from** (verified on the box 2026-08-27):
the Pi 5's only hardware video decoder is `rpivid` at `/dev/video19`, and it
advertises exactly one coded format:

```
[0]: 'S265' (HEVC Parsed Slice Data, compressed)
```

No H.264, no VP9, no AV1 -- those all fall back to CPU decoding. `kodi.log`
shows it happening on every H.264 play:

```
Creating video codec with codec id: 27          <- H.264
DRMPRIME::Open - using decoder V4L2 mem2mem H.264 decoder wrapper
DRMPRIME::Open - unable to open codec           <- hardware refuses
DRMPRIME::Open - using decoder H.264 / AVC ...  <- CPU fallback
```

Software decode is comfortable at 1080p and falls over at 4K. And YouTube never
serves HEVC -- above 1080p it only offers AV1 and VP9. So **the only way to get
4K onto that box is to re-encode it to HEVC.**

So the rule keys on the hardware, not on the file extension:

| Downloaded stream | What happens |
|---|---|
| HEVC, any resolution | kept as-is (hardware path) |
| Anything within the **1080p pixel budget** (1920x1080 +10%) | kept as-is (CPU decode is fine; re-encoding would only lose quality) |
| Anything else (4K AV1 / VP9 / H.264) | re-encoded to **HEVC MP4** |
| Instagram (gallery-dl) | never touched |

The budget is **total pixels, not height** — decode cost scales with pixel
count. A 1080x1920 vertical clip has the same 2,073,600 pixels as 1080p
landscape and is left alone; an earlier version of this rule compared height
against 1080 and needlessly transcoded vertical video.

Audio is never re-encoded: AAC is preferred at format-selection time and copied
straight across.

**4K HDR is the quality ceiling this targets, and it survives the re-encode.**
yt-dlp's default sort already prefers the HDR variant at a given resolution, and
the re-encode carries HDR across intact -- verified on a 4K HDR10 rip:

| | Source (as downloaded) | Output (after re-encode) |
|---|---|---|
| codec | vp9 Profile 2 | **hevc Main 10** |
| pix_fmt | yuv420p10le | yuv420p10le |
| primaries / transfer / matrix | bt2020 / smpte2084 / bt2020nc | bt2020 / smpte2084 / bt2020nc |
| mastering display metadata | present | **present** |

`rpivid` advertises a 10-bit capture format (`NC30`), so Main10 hardware-decodes
on the Pi as well.

Encoding uses **NVENC** where available (`hevc_nvenc`), falling back to
`libx265`. Measured on an RTX 4070 SUPER against a 4K30 AV1 source: presets
p4..p7 all produced the *same* output size, so the app uses `p5` at ~1.2x
real-time. Decoding is not the bottleneck (software AV1 decode of the same clip
ran ~187 fps), which is why there's no `-hwaccel` flag -- it was measured and
made no difference.

Downloads are capped at 2160p: the Pi's decoder tops out around 4K and the
display is 4K, so an 8K rip would only burn disk and stall playback.

**Verified end-to-end 2026-08-27:** a 4K AV1 YouTube rip was re-encoded to HEVC
Main, copied to the NAS and played on the Pi -- playback advanced 12.1 s of
video in 12.0 s of wall clock (1.01x, no dropped frames) and Kodi opened it on
the DRMPRIME hardware path with no fallback line.

### The 1080p toggle, exactly

When **on**, yt-dlp gets:

```
-f "bv*[ext=mp4][vcodec^=avc1][height<=1080]+ba[ext=m4a]/b[ext=mp4][vcodec^=avc1][height<=1080]"
--merge-output-format mp4
```

Pre-encoded H.264 video + AAC audio at <=1080p, remuxed into MP4 -- no
transcode. If a site has no H.264 MP4 stream, that link errors rather than
silently falling back to webm.

---

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| "Video unavailable" / "user could not be found" | Anonymous block. Add a `cookies.txt`. |
| "Sign in to confirm you're not a bot" / "cookies are no longer valid" | YouTube wants a valid login and your cookies have rotated/expired. Re-export via the **Incognito method** (see Cookies section) -- normal exports go stale fast. |
| "Could not copy Chrome cookie database" | You're trying browser cookies -- not supported; export `cookies.txt` instead. |
| Output is `.webm` and you wanted `.mp4` | Shouldn't happen with **Kodi / Pi 5 mode** on -- it lands everything in MP4. If it's off, tick it (or the 1080p toggle). |
| 4K rip stutters in Kodi on the Pi | It wasn't re-encoded -- check the log for a `-> HEVC` line. Only HEVC hardware-decodes on a Pi 5. |
| Re-encode is slow | It runs ~1.2x real-time for 4K30 on an RTX 4070 SUPER; encoding is the bottleneck. Lower `HEVC_PRESET` (p5 -> p4) in `ripper.pyw` to trade a little quality for speed. |
| Re-encoded file is bigger than expected | Depends on the source bitrate: a 110 MB 4K AV1 grew to 169 MB, but a 230 MB 4K HDR VP9 shrank to 149 MB. Raise `HEVC_CQ` in `ripper.pyw` to trade quality for size. |
| yt-dlp fails on a site that used to work | Sites change constantly: `pip install -U yt-dlp gallery-dl`. |
| "ffmpeg not found" in the log | Install ffmpeg and ensure it's on PATH. |

---

## License / scope

Personal utility. Respect the terms of service and copyright of the sites you
download from; only rip content you have the right to.
