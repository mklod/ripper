# Ripper - one-click link downloader (yt-dlp + gallery-dl)
# Last modified: 2026-08-27--2340
#
# Paste one or many links, click Rip. Instagram URLs route to gallery-dl
# (handles reels, photos, carousels, profiles, stories); everything else
# goes to yt-dlp (YouTube, TikTok, X, etc.).

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

APP_DIR = Path(__file__).resolve().parent

# Runtime state (config + the merged cookies temp file) is kept in a per-user
# local dir, NOT next to the script. The script may live on a guest-readable
# network share; merged cookies are live session secrets and must stay local.
if os.name == "nt":
    STATE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Ripper"
else:
    STATE_DIR = Path.home() / ".config" / "ripper"
STATE_DIR.mkdir(parents=True, exist_ok=True)

CONFIG = STATE_DIR / "ripper_config.json"
MERGED_COOKIES = STATE_DIR / "_cookies_merged.txt"
DEFAULT_OUT = str(Path.home() / "Downloads" / "Ripper")

# When the "Force 1080p H.264 MP4" toggle is on: pick pre-encoded H.264 mp4
# video + m4a audio at <=1080p, with a fallback to a single-file H.264 mp4.
# No webm/vp9 fallback (the toggle means "force mp4"), and no --recode-video
# anywhere, so merging is just a container remux - never a re-encode.
FORMAT_1080_MP4 = ("bv*[ext=mp4][vcodec^=avc1][height<=1080]+ba[ext=m4a]/"
                   "b[ext=mp4][vcodec^=avc1][height<=1080]")

# Default: best available quality, capped at 4K. The cap is deliberate --
# the Pi 5's hardware decoder tops out around 4K and the display is 4K, so an
# 8K rip would only burn disk and stall playback. AAC audio is preferred at
# selection time so the audio track never needs re-encoding downstream.
FORMAT_BEST_4K = ("bv*[height<=2160]+ba[ext=m4a]/bv*[height<=2160]+ba/"
                  "b[height<=2160]/bv*+ba/b")

# --- Kodi / Raspberry Pi 5 compatibility ---------------------------------
# Verified on the box (2026-08-27): the Pi 5's only hardware video decoder is
# rpivid (/dev/video19) and it advertises exactly one coded format, 'S265'
# (HEVC) -- with a 10-bit capture format (NC30) so HDR/Main10 is covered.
# H.264, VP9 and AV1 all fall back to CPU decoding; kodi.log shows the V4L2
# H.264 wrapper failing to open and handing off to software on every play.
# Software decode is comfortable at 1080p and falls over at 4K. So the rule
# keys on the hardware, not on the codec name: keep anything HEVC (hardware
# path) and anything <=1080p (software path is fine, and re-encoding it would
# only throw quality away); re-encode everything else. That covers 4K AV1/VP9
# from YouTube and also 4K H.264 from other sites, which the Pi 5 can't
# hardware-decode either.
KEEP_CODECS = {"hevc", "h265"}   # the only codec rpivid will accept
SW_SAFE_HEIGHT = 1080            # CPU decode is comfortable up to here
HEVC_CQ = 21          # NVENC constant-quality target (lower = bigger/better)
HEVC_CRF = 20         # libx265 fallback quality
# Measured on the RTX 4070 SUPER over a 4K30 AV1 source (2026-08-27): presets
# p4..p7 all produced the SAME output size (50.5 MB for a 20s slice) while
# p7 took 21.6s and p4 13.2s -- the slower presets buy nothing here. p5 sits
# at ~1.2x realtime for 4K30. Encoding is the bottleneck, not decoding
# (software AV1 decode of the same clip runs ~187 fps), so there is no point
# adding -hwaccel; it was measured and made no difference.
HEVC_PRESET = "p5"
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}
LAST_FILES = STATE_DIR / "_last_files.txt"

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def load_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(data):
    try:
        CONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def is_instagram(url):
    return "instagram.com" in url.lower()


class RipperApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        # One-time migration from the old single-file + browser config keys.
        if "cookie_files" not in self.cfg:
            old = (self.cfg.get("cookiefile") or "").strip()
            self.cfg["cookie_files"] = [old] if old else []

        self.log_q = queue.Queue()
        self.proc = None
        self.cancelled = False
        self.ffmpeg = shutil.which("ffmpeg")
        self.hevc_encoder = self.pick_hevc_encoder()

        root.title("Ripper")
        root.geometry("680x720")
        root.minsize(560, 560)

        pad = dict(padx=10, pady=6)

        # Uniform widths so the path entry and cookie listbox line up on both edges.
        LABEL_W = 13
        BTN_W = 8

        ttk.Label(root, text="Paste links (one per line):").pack(anchor="w", **pad)

        # --- links + Rip/Cancel (Rip sits right next to the paste box) ---
        links_row = ttk.Frame(root)
        links_row.pack(fill="x", padx=10)
        self.urls = tk.Text(links_row, height=7, wrap="none", font=("Consolas", 10))
        self.urls.pack(side="left", fill="both", expand=True)
        rip_col = ttk.Frame(links_row)
        rip_col.pack(side="left", fill="y", padx=(6, 0))
        self.rip_btn = ttk.Button(rip_col, text="Rip", command=self.start, width=BTN_W)
        self.rip_btn.pack(fill="x", ipady=10)
        self.cancel_btn = ttk.Button(rip_col, text="Cancel", command=self.cancel,
                                     state="disabled", width=BTN_W)
        self.cancel_btn.pack(fill="x", pady=(4, 0), ipady=2)

        # --- output folder row ---
        out_row = ttk.Frame(root)
        out_row.pack(fill="x", **pad)
        ttk.Label(out_row, text="Save to:", width=LABEL_W, anchor="w").pack(side="left")
        self.out_var = tk.StringVar(value=self.cfg.get("outdir", DEFAULT_OUT))
        self.out_entry = ttk.Entry(out_row, textvariable=self.out_var)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(out_row, text="Browse", width=BTN_W,
                   command=self.pick_folder).pack(side="left")

        # --- cookies files (multi) ---
        ck_row = ttk.Frame(root)
        ck_row.pack(fill="x", padx=10, pady=(0, 6))
        ttk.Label(ck_row, text="Cookie files:", width=LABEL_W, anchor="nw").pack(
            side="left", anchor="n", pady=(2, 0))
        lb_wrap = ttk.Frame(ck_row)
        lb_wrap.pack(side="left", fill="x", expand=True, padx=6)
        self.cookie_lb = tk.Listbox(lb_wrap, height=3, selectmode="extended",
                                    exportselection=False, activestyle="none")
        self.cookie_lb.pack(side="left", fill="x", expand=True)
        lb_sb = ttk.Scrollbar(lb_wrap, command=self.cookie_lb.yview)
        lb_sb.pack(side="left", fill="y")
        self.cookie_lb.configure(yscrollcommand=lb_sb.set)
        for f in self.cfg.get("cookie_files", []):
            if f:
                self.cookie_lb.insert("end", f)
        ck_btns = ttk.Frame(ck_row)
        ck_btns.pack(side="left")
        ttk.Button(ck_btns, text="Add", command=self.add_cookies, width=BTN_W).pack(fill="x")
        ttk.Button(ck_btns, text="Remove", command=self.remove_cookies, width=BTN_W).pack(
            fill="x", pady=(2, 0))

        # --- quality toggle (read fresh at every Rip click) ---
        q_row = ttk.Frame(root)
        q_row.pack(fill="x", padx=10, pady=(0, 6))
        self.force_mp4_var = tk.BooleanVar(value=self.cfg.get("force_1080_mp4", False))
        ttk.Checkbutton(
            q_row, variable=self.force_mp4_var,
            text="Force 1080p H.264 MP4  (no re-encode; off = best available)"
        ).pack(side="left")

        k_row = ttk.Frame(root)
        k_row.pack(fill="x", padx=10, pady=(0, 6))
        self.kodi_var = tk.BooleanVar(value=self.cfg.get("kodi_hevc", True))
        ttk.Checkbutton(
            k_row, variable=self.kodi_var,
            text="Kodi/Pi 5 mode: re-encode AV1 / VP9 -> HEVC MP4  (keeps 4K)"
        ).pack(side="left")

        # --- utility buttons ---
        btn_row = ttk.Frame(root)
        btn_row.pack(fill="x", **pad)
        ttk.Button(btn_row, text="Clear log", command=self.clear_log).pack(side="left")
        ttk.Button(btn_row, text="Copy log", command=self.copy_log).pack(
            side="left", padx=8)
        self.update_btn = ttk.Button(btn_row, text="Update yt-dlp / gallery-dl",
                                     command=self.update_deps)
        self.update_btn.pack(side="right")

        # --- log ---
        log_frame = ttk.Frame(root)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.log = tk.Text(log_frame, wrap="word", font=("Consolas", 9),
                           background="#1e1e1e", foreground="#d4d4d4", state="disabled")
        sb = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)
        self.log.tag_config("err", foreground="#f48771")
        self.log.tag_config("ok", foreground="#89d185")
        self.log.tag_config("info", foreground="#569cd6")

        self.status = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status, relief="sunken",
                  anchor="w").pack(fill="x", side="bottom")

        # Right-click context menus on text fields.
        self.attach_ctx_menu(self.urls)
        self.attach_ctx_menu(self.out_entry)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(120, self.drain_log)

        if not self.ffmpeg:
            self.write("ffmpeg not found on PATH - video merging may fail.\n", "err")

    # ---------- logging ----------
    def write(self, text, tag=None):
        self.log_q.put((text, tag))

    def drain_log(self):
        try:
            while True:
                text, tag = self.log_q.get_nowait()
                self.log.configure(state="normal")
                self.log.insert("end", text, tag or ())
                self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(120, self.drain_log)

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ---------- folder & cookies helpers ----------
    def pick_folder(self):
        d = filedialog.askdirectory(initialdir=self.out_var.get() or DEFAULT_OUT)
        if d:
            self.out_var.set(d)

    def copy_log(self):
        text = self.log.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.set_status("Log copied to clipboard")

    # ---------- dependency update ----------
    def update_deps(self):
        """Update yt-dlp + gallery-dl (they break when sites change). Streams the
        pip output into the log; disables Rip/Update while it runs."""
        self.update_btn.configure(state="disabled")
        self.rip_btn.configure(state="disabled")
        self.write("\n=== Updating yt-dlp + gallery-dl ===\n", "info")
        self.set_status("Updating dependencies...")
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        cmd = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "gallery-dl"]
        try:
            rc = self.run_one(cmd)
        except Exception as e:
            self.write(f"  error: {e}\n", "err")
            rc = -1
        if rc == 0:
            self.write("  updated.\n", "ok")
            for mod, label in (("yt_dlp", "yt-dlp"), ("gallery_dl", "gallery-dl")):
                try:
                    out = subprocess.run(
                        [sys.executable, "-m", mod, "--version"],
                        capture_output=True, text=True, creationflags=NO_WINDOW)
                    ver = (out.stdout or "").strip().splitlines()[0]
                    self.write(f"  {label}: {ver}\n", "ok")
                except Exception:
                    pass
            self.set_status("Dependencies updated")
        else:
            self.write(f"  update failed (exit {rc})\n", "err")
            self.set_status("Dependency update failed")
        self.root.after(0, self.reset_buttons)

    def add_cookies(self):
        files = filedialog.askopenfilenames(
            title="Add cookies file(s)",
            filetypes=[("Cookies file", "*.txt"), ("All files", "*.*")])
        existing = set(self.cookie_lb.get(0, "end"))
        for f in files:
            if f not in existing:
                self.cookie_lb.insert("end", f)
                existing.add(f)

    def remove_cookies(self):
        for i in reversed(self.cookie_lb.curselection()):
            self.cookie_lb.delete(i)

    def cookie_paths(self):
        out = []
        for i in range(self.cookie_lb.size()):
            p = self.cookie_lb.get(i)
            if p and Path(p).is_file():
                out.append(p)
        return out

    # ---------- right-click context menu ----------
    def attach_ctx_menu(self, widget):
        m = tk.Menu(widget, tearoff=0)
        m.add_command(label="Cut",    command=lambda: widget.event_generate("<<Cut>>"))
        m.add_command(label="Copy",   command=lambda: widget.event_generate("<<Copy>>"))
        m.add_command(label="Paste",  command=lambda: widget.event_generate("<<Paste>>"))
        m.add_separator()
        m.add_command(label="Select all", command=lambda: self.select_all(widget))
        widget.bind("<Button-3>", lambda e: m.tk_popup(e.x_root, e.y_root))

    def select_all(self, w):
        if isinstance(w, tk.Text):
            w.tag_add("sel", "1.0", "end-1c")
            w.mark_set("insert", "1.0")
        else:
            w.select_range(0, "end")
            w.icursor("end")
        w.focus_set()
        return "break"

    # ---------- run control ----------
    def start(self):
        raw = self.urls.get("1.0", "end").splitlines()
        links = [u.strip() for u in raw if u.strip().lower().startswith("http")]
        if not links:
            self.status.set("No valid links - paste http(s) URLs, one per line")
            return

        outdir = self.out_var.get().strip() or DEFAULT_OUT
        Path(outdir).mkdir(parents=True, exist_ok=True)
        save_config({
            "outdir": outdir,
            "cookie_files": list(self.cookie_lb.get(0, "end")),
            "force_1080_mp4": self.force_mp4_var.get(),
            "kodi_hevc": self.kodi_var.get(),
        })

        self.cancelled = False
        self.rip_btn.configure(state="disabled")
        self.update_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        if self.force_mp4_var.get():
            mode = "1080p mp4"
        elif self.kodi_var.get():
            mode = f"best quality -> Kodi/Pi5 HEVC ({self.hevc_encoder})"
        else:
            mode = "best quality"
        self.write(f"\n=== Ripping {len(links)} link(s) -> {outdir}  [{mode}] ===\n",
                   "info")

        threading.Thread(target=self.worker, args=(links, outdir), daemon=True).start()

    def cancel(self):
        self.cancelled = True
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
        self.write("Cancelled by user.\n", "err")

    # ---------- backend command builders ----------
    def cookie_args(self):
        """Both backends accept --cookies <file>, but only one file each. To
        support Instagram + YouTube simultaneously, concatenate cookies.txt
        files into a temp file. The Netscape format is line-oriented; comment
        and per-domain lines don't collide."""
        paths = self.cookie_paths()
        if not paths:
            return []
        if len(paths) == 1:
            return ["--cookies", paths[0]]
        try:
            with MERGED_COOKIES.open("w", encoding="utf-8") as out:
                for p in paths:
                    out.write(Path(p).read_text(encoding="utf-8", errors="replace"))
                    out.write("\n")
            return ["--cookies", str(MERGED_COOKIES)]
        except Exception as e:
            self.write(f"  cookie merge failed ({e}); proceeding without\n", "err")
            return []

    def build_cmd(self, url, outdir):
        cookies = self.cookie_args()
        if is_instagram(url):
            cmd = [sys.executable, "-m", "gallery_dl", "-D", outdir]
            cmd += cookies
        else:
            cmd = [sys.executable, "-m", "yt_dlp", "--newline", "--no-mtime",
                   "-P", outdir, "-o", "%(title)s [%(id)s].%(ext)s"]
            if self.ffmpeg:
                cmd += ["--ffmpeg-location", self.ffmpeg]
            if self.force_mp4_var.get():
                cmd += ["-f", FORMAT_1080_MP4, "--merge-output-format", "mp4"]
            else:
                # Best available (<=4K), landed in an mp4 container. --remux-video
                # also catches single-file downloads that never hit the merger.
                cmd += ["-f", FORMAT_BEST_4K,
                        "--merge-output-format", "mp4",
                        "--remux-video", "mp4"]
            # Record the finished file(s) so the worker can post-process them.
            cmd += ["--print-to-file", "after_move:%(filepath)s", str(LAST_FILES)]
            cmd += cookies
        cmd.append(url)
        return cmd

    def worker(self, links, outdir):
        ok = fail = 0
        for i, url in enumerate(links, 1):
            if self.cancelled:
                break
            backend = "gallery-dl" if is_instagram(url) else "yt-dlp"
            self.write(f"\n[{i}/{len(links)}] {backend}: {url}\n", "info")
            self.set_status(f"[{i}/{len(links)}] downloading...")
            try:
                LAST_FILES.unlink(missing_ok=True)
                rc = self.run_one(self.build_cmd(url, outdir))
            except Exception as e:
                self.write(f"  error: {e}\n", "err")
                rc = -1
            if rc == 0:
                if backend == "yt-dlp" and self.kodi_var.get() and not self.cancelled:
                    self.kodi_pass()
                ok += 1
                self.write("  done\n", "ok")
            else:
                fail += 1
                if not self.cancelled:
                    self.write(f"  failed (exit {rc})\n", "err")

        summary = f"Finished: {ok} ok, {fail} failed"
        self.write(f"\n=== {summary} ===\n", "ok" if fail == 0 else "err")
        self.set_status(summary)
        self.root.after(0, self.reset_buttons)

    # ---------- Kodi / Pi 5 compatibility pass ----------
    def pick_hevc_encoder(self):
        """NVENC if this machine has it (near-free on a modern GPU), else x265."""
        try:
            out = subprocess.run([self.ffmpeg or "ffmpeg", "-hide_banner", "-encoders"],
                                 capture_output=True, text=True,
                                 creationflags=NO_WINDOW).stdout or ""
        except Exception:
            return "libx265"
        return "hevc_nvenc" if "hevc_nvenc" in out else "libx265"

    def probe(self, path):
        """Read the stream properties we need to decide on (and configure) a
        re-encode. Returns None if ffprobe isn't usable."""
        probe_bin = "ffprobe"
        if self.ffmpeg:
            cand = Path(self.ffmpeg).with_name("ffprobe.exe" if os.name == "nt"
                                               else "ffprobe")
            if cand.is_file():
                probe_bin = str(cand)
        fields = ("stream=codec_name,codec_type,height,"
                  "color_transfer,color_primaries,color_space")
        try:
            out = subprocess.run(
                [probe_bin, "-v", "error", "-show_entries", fields,
                 "-of", "json", str(path)],
                capture_output=True, text=True, creationflags=NO_WINDOW)
            data = json.loads(out.stdout or "{}")
        except Exception as e:
            self.write(f"  ffprobe failed ({e}); leaving file as-is\n", "err")
            return None
        info = {"vcodec": "", "acodec": "", "height": 0,
                "trc": "", "prim": "", "space": ""}
        for st in data.get("streams", []):
            if st.get("codec_type") == "video" and not info["vcodec"]:
                info["vcodec"] = (st.get("codec_name") or "").lower()
                info["height"] = int(st.get("height") or 0)
                info["trc"] = (st.get("color_transfer") or "").lower()
                info["prim"] = (st.get("color_primaries") or "").lower()
                info["space"] = (st.get("color_space") or "").lower()
            elif st.get("codec_type") == "audio" and not info["acodec"]:
                info["acodec"] = (st.get("codec_name") or "").lower()
        return info

    def transcode_cmd(self, src, dst, info):
        """AV1/VP9 -> HEVC, video only. Audio is copied when it's already AAC.
        Colour tags are carried across so HDR still flags as HDR in Kodi."""
        hdr = info["trc"] in HDR_TRANSFERS
        cmd = [self.ffmpeg or "ffmpeg", "-y", "-hide_banner",
               "-loglevel", "warning", "-stats", "-stats_period", "2",
               "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?",
               "-c:v", self.hevc_encoder]
        if self.hevc_encoder == "hevc_nvenc":
            cmd += ["-preset", HEVC_PRESET, "-tune", "hq", "-rc", "vbr",
                    "-cq", str(HEVC_CQ), "-b:v", "0",
                    "-profile:v", "main10" if hdr else "main",
                    "-pix_fmt", "p010le" if hdr else "yuv420p"]
        else:
            cmd += ["-preset", "medium", "-crf", str(HEVC_CRF),
                    "-profile:v", "main10" if hdr else "main",
                    "-pix_fmt", "yuv420p10le" if hdr else "yuv420p"]
        for flag, val in (("-color_primaries", info["prim"]),
                          ("-color_trc", info["trc"]),
                          ("-colorspace", info["space"])):
            if val and val not in ("unknown", "reserved"):
                cmd += [flag, val]
        if info["acodec"] == "aac":
            cmd += ["-c:a", "copy"]
        else:
            cmd += ["-c:a", "aac", "-b:a", "192k"]
        cmd += ["-tag:v", "hvc1", "-movflags", "+faststart", str(dst)]
        return cmd

    def kodi_pass(self):
        """Re-encode anything the Pi 5 can't hardware-decode. Reads the file
        list yt-dlp just wrote; H.264/HEVC are left untouched."""
        try:
            paths = [ln.strip() for ln in
                     LAST_FILES.read_text(encoding="utf-8", errors="replace").splitlines()
                     if ln.strip()]
        except Exception:
            return
        for raw in paths:
            src = Path(raw)
            if self.cancelled or not src.is_file():
                continue
            info = self.probe(src)
            if not info:
                continue
            if (info["vcodec"] in KEEP_CODECS
                    or info["height"] <= SW_SAFE_HEIGHT):
                why = ("hardware-decoded" if info["vcodec"] in KEEP_CODECS
                       else "software-decodes fine")
                self.write(f"  {info['vcodec']} {info['height']}p - {why}, "
                           f"no re-encode\n", "ok")
                continue
            hdr = " HDR" if info["trc"] in HDR_TRANSFERS else ""
            self.write(f"  {info['vcodec']} {info['height']}p{hdr} -> HEVC "
                       f"({self.hevc_encoder})...\n", "info")
            self.set_status(f"re-encoding {src.name} -> HEVC...")
            tmp = src.with_name(src.stem + ".__hevc.mp4")
            final = src.with_suffix(".mp4")
            try:
                rc = self.run_one(self.transcode_cmd(src, tmp, info))
            except Exception as e:
                self.write(f"  re-encode error: {e}\n", "err")
                rc = -1
            if rc != 0 or not tmp.is_file():
                self.write("  re-encode failed - keeping the original file\n", "err")
                try:
                    tmp.unlink(missing_ok=True)
                except Exception:
                    pass
                continue
            try:
                src.unlink()
                os.replace(tmp, final)
                self.write(f"  -> {final.name}\n", "ok")
            except Exception as e:
                self.write(f"  could not replace original ({e}); "
                           f"re-encode left at {tmp.name}\n", "err")

    def run_one(self, cmd):
        self.proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, encoding="utf-8", errors="replace",
            creationflags=NO_WINDOW)
        for line in self.proc.stdout:
            self.write("  " + line)
        self.proc.wait()
        rc = self.proc.returncode
        self.proc = None
        return rc

    # ---------- ui helpers (thread-safe) ----------
    def set_status(self, text):
        self.root.after(0, lambda: self.status.set(text))

    def reset_buttons(self):
        self.rip_btn.configure(state="normal")
        self.update_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")

    def on_close(self):
        self.cancelled = True
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except Exception:
                pass
        try:
            MERGED_COOKIES.unlink(missing_ok=True)
        except Exception:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.call("ttk::style", "theme", "use", "vista")
    except tk.TclError:
        pass
    RipperApp(root)
    root.mainloop()
