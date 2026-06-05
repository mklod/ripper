# Ripper - one-click link downloader (yt-dlp + gallery-dl)
# Last modified: 2026-06-05--0149
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

        root.title("Ripper")
        root.geometry("680x720")
        root.minsize(560, 560)

        pad = dict(padx=10, pady=6)

        ttk.Label(root, text="Paste links (one per line):").pack(anchor="w", **pad)
        self.urls = tk.Text(root, height=7, wrap="none", font=("Consolas", 10))
        self.urls.pack(fill="x", padx=10)

        # --- output folder row ---
        out_row = ttk.Frame(root)
        out_row.pack(fill="x", **pad)
        ttk.Label(out_row, text="Save to:").pack(side="left")
        self.out_var = tk.StringVar(value=self.cfg.get("outdir", DEFAULT_OUT))
        self.out_entry = ttk.Entry(out_row, textvariable=self.out_var)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(out_row, text="Browse", command=self.pick_folder).pack(side="left")
        ttk.Button(out_row, text="Open", command=self.open_folder).pack(
            side="left", padx=(6, 0))

        # --- cookies files (multi) ---
        ck_row = ttk.Frame(root)
        ck_row.pack(fill="x", padx=10, pady=(0, 6))
        ttk.Label(ck_row, text="Cookie files:").pack(side="left", anchor="n", pady=(2, 0))
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
        ttk.Button(ck_btns, text="Add", command=self.add_cookies, width=8).pack(fill="x")
        ttk.Button(ck_btns, text="Remove", command=self.remove_cookies, width=8).pack(
            fill="x", pady=(2, 0))

        # --- quality toggle (read fresh at every Rip click) ---
        q_row = ttk.Frame(root)
        q_row.pack(fill="x", padx=10, pady=(0, 6))
        self.force_mp4_var = tk.BooleanVar(value=self.cfg.get("force_1080_mp4", False))
        ttk.Checkbutton(
            q_row, variable=self.force_mp4_var,
            text="Force 1080p H.264 MP4  (no re-encode; off = best available)"
        ).pack(side="left")

        # --- action buttons ---
        btn_row = ttk.Frame(root)
        btn_row.pack(fill="x", **pad)
        self.rip_btn = ttk.Button(btn_row, text="Rip", command=self.start)
        self.rip_btn.pack(side="left", ipadx=20, ipady=4)
        self.cancel_btn = ttk.Button(btn_row, text="Cancel", command=self.cancel,
                                     state="disabled")
        self.cancel_btn.pack(side="left", padx=8, ipady=4)
        ttk.Button(btn_row, text="Clear log", command=self.clear_log).pack(side="left")

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

    def open_folder(self):
        d = self.out_var.get()
        Path(d).mkdir(parents=True, exist_ok=True)
        os.startfile(d)

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
        })

        self.cancelled = False
        self.rip_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        mode = "1080p mp4" if self.force_mp4_var.get() else "best quality"
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
                rc = self.run_one(self.build_cmd(url, outdir))
            except Exception as e:
                self.write(f"  error: {e}\n", "err")
                rc = -1
            if rc == 0:
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
