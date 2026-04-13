"""
app.py — Soft journalling GUI for the Mood Diary.
Light mode: warm cream + sage.  Dark mode: deep purple-night + violet.
Toggle between them with the moon/sun button in the sidebar.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
import os, sys, urllib.request

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

import database as db
import mood_engine as me
import charts

# ── Font download (Nunito) ─────────────────────────────────────────────────────
_FONT_DIR   = os.path.join(os.path.dirname(__file__), "_fonts")
_FONT_FILE  = os.path.join(_FONT_DIR, "Nunito-Regular.ttf")
_FONT_BOLD  = os.path.join(_FONT_DIR, "Nunito-Bold.ttf")
_FONT_URLS  = {
    _FONT_FILE: "https://github.com/googlefonts/nunito/raw/main/fonts/TTF/Nunito-Regular.ttf",
    _FONT_BOLD: "https://github.com/googlefonts/nunito/raw/main/fonts/TTF/Nunito-Bold.ttf",
}

def _try_load_fonts():
    try:
        os.makedirs(_FONT_DIR, exist_ok=True)
        for path, url in _FONT_URLS.items():
            if not os.path.exists(path):
                urllib.request.urlretrieve(url, path)
        import matplotlib.font_manager as fm
        for path in _FONT_URLS:
            if os.path.exists(path):
                fm.fontManager.addfont(path)
        if sys.platform == "win32":
            import ctypes
            for path in _FONT_URLS:
                if os.path.exists(path):
                    ctypes.windll.gdi32.AddFontResourceW(path)
    except Exception:
        pass

# ── Theme palettes ─────────────────────────────────────────────────────────────
THEMES = {
    "light": {
        "bg":        "#FAF7F2",
        "bg2":       "#F3EDE3",
        "bg3":       "#EDE5D8",
        "bg4":       "#E5DACE",
        "stroke":    "#D9CEBB",
        "text":      "#5C4F3D",
        "text2":     "#9B8B78",
        "text3":     "#C4B5A2",
        "accent":    "#8BAF8B",
        "accent2":   "#A8C5A8",
        "rose":      "#C9808A",
        "rose2":     "#DDA8B0",
        "teal":      "#7BAF9E",
        "lavender":  "#B5A8CE",
        "header_fg": "#D6EDD6",
        "tab_sel":   "#8BAF8B",
        "stat_val":  "#8BAF8B",
    },
    "dark": {
        "bg":        "#16121F",
        "bg2":       "#1E1830",
        "bg3":       "#261F3D",
        "bg4":       "#2F274A",
        "stroke":    "#3A3055",
        "text":      "#E8E2F5",
        "text2":     "#9F94C0",
        "text3":     "#6A5F8A",
        "accent":    "#9B7FD4",
        "accent2":   "#B89FE8",
        "rose":      "#C47A9A",
        "rose2":     "#D9A0BA",
        "teal":      "#7A9EC4",
        "lavender":  "#A890D0",
        "header_fg": "#C8B8F0",
        "tab_sel":   "#7B5FC4",
        "stat_val":  "#B89FE8",
    },
}

C = dict(THEMES["light"])

# ── Font stack ─────────────────────────────────────────────────────────────────
def _pick_font():
    candidates = ["Nunito", "Varela Round", "Quicksand",
                  "Trebuchet MS", "Gill Sans", "Segoe UI"]
    import tkinter.font as tkfont
    try:
        available = tkfont.families()
        for f in candidates:
            if f in available:
                return f
    except Exception:
        pass
    return "Helvetica"

_F = None


class MoodJournal:
    def __init__(self):
        db.init_db()
        _try_load_fonts()

        self.root = tk.Tk()
        self.root.title("dear diary")
        self.root.geometry("1240x760")
        self.root.minsize(960, 620)

        global _F
        _F = _pick_font()

        self._editing_id   = None
        self._preview_job  = None
        self._chart_widget = None
        self._dark_mode    = False
        self._themed_widgets = []

        self._build_styles()
        self._build_ui()
        self._refresh_stats()
        self._load_entries()

    # ── ttk Styles ─────────────────────────────────────────────────────────────
    def _build_styles(self):
        self._apply_ttk_styles()

    def _apply_ttk_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("TFrame",        background=C["bg"])
        s.configure("TLabel",        background=C["bg"],  foreground=C["text"],
                                     font=(_F, 10))
        s.configure("TNotebook",     background=C["bg"],  borderwidth=0)
        s.configure("TNotebook.Tab", background=C["bg3"], foreground=C["text2"],
                                     padding=(18, 8), font=(_F, 10))
        s.map("TNotebook.Tab",
              background=[("selected", C["tab_sel"])],
              foreground=[("selected", "white")])
        s.configure("Treeview",
                     background=C["bg2"], foreground=C["text"],
                     fieldbackground=C["bg2"], rowheight=36,
                     font=(_F, 9), borderwidth=0)
        s.configure("Treeview.Heading",
                     background=C["bg3"], foreground=C["text2"],
                     font=(_F, 9), relief="flat")
        s.map("Treeview", background=[("selected", C["accent2"])])
        s.configure("Vertical.TScrollbar",
                     background=C["bg3"], troughcolor=C["bg2"],
                     arrowcolor=C["text3"], borderwidth=0, relief="flat")
        s.configure("TCombobox",
                     fieldbackground=C["bg3"], background=C["bg3"],
                     foreground=C["text"], selectbackground=C["accent2"],
                     font=(_F, 9))

    # ── Root layout ────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.root.configure(bg=C["bg"])
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    # ── Sidebar ────────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg=C["bg2"], width=214)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self._tw(self.sidebar, bg="bg2")

        self.sb_header = tk.Frame(self.sidebar, bg=C["accent"], height=68)
        self.sb_header.pack(fill="x")
        self._tw(self.sb_header, bg="accent")

        self.lbl_title = tk.Label(self.sb_header, text="dear diary",
                                   bg=C["accent"], fg="white",
                                   font=(_F, 16, "bold"))
        self.lbl_title.pack(pady=(10, 0))
        self._tw(self.lbl_title, bg="accent", fg_fixed="white")

        self.lbl_sub = tk.Label(self.sb_header, text="your safe space",
                                 bg=C["accent"], fg=C["header_fg"],
                                 font=(_F, 8))
        self.lbl_sub.pack()
        self._tw(self.lbl_sub, bg="accent", fg="header_fg")

        top_row = tk.Frame(self.sidebar, bg=C["bg2"])
        top_row.pack(fill="x", padx=14, pady=(10, 0))
        self._tw(top_row, bg="bg2")

        self.lbl_date = tk.Label(top_row,
                                  text=datetime.now().strftime("%A, %d %B"),
                                  bg=C["bg2"], fg=C["text2"],
                                  font=(_F, 9, "italic"))
        self.lbl_date.pack(side="left")
        self._tw(self.lbl_date, bg="bg2", fg="text2")

        self.btn_theme = tk.Button(top_row, text="🌙",
                                    bg=C["bg3"], fg=C["text2"],
                                    font=(_F, 11), relief="flat",
                                    cursor="hand2", padx=6, pady=1,
                                    activebackground=C["bg4"],
                                    command=self._toggle_theme)
        self.btn_theme.pack(side="right")
        self._tw(self.btn_theme, bg="bg3", fg="text2", hover="bg4")

        self.stats_frame = tk.Frame(self.sidebar, bg=C["bg2"])
        self.stats_frame.pack(fill="x", padx=14, pady=10)
        self._tw(self.stats_frame, bg="bg2")
        self.lbl_total  = self._stat_pill(self.stats_frame, "0", "entries written")
        self.lbl_streak = self._stat_pill(self.stats_frame, "0", "day streak")
        self.lbl_top    = self._stat_pill(self.stats_frame, "--", "recent mood")

        self.div1 = tk.Frame(self.sidebar, bg=C["stroke"], height=1)
        self.div1.pack(fill="x", padx=14)
        self._tw(self.div1, bg="stroke")

        nav = tk.Frame(self.sidebar, bg=C["bg2"])
        nav.pack(fill="x", padx=14, pady=10)
        self._tw(nav, bg="bg2")

        self.lbl_pages = tk.Label(nav, text="pages", bg=C["bg2"],
                                   fg=C["text3"], font=(_F, 8))
        self.lbl_pages.pack(anchor="w", pady=(0, 4))
        self._tw(self.lbl_pages, bg="bg2", fg="text3")

        self._nav_btns = []
        for label, idx in [("write",    0), ("entries",  1), ("insights", 2)]:
            symbols = {"write": "✦", "entries": "◈", "insights": "◎"}
            btn = tk.Button(nav, text=f"{symbols[label]}  {label}",
                            bg=C["bg3"], fg=C["text"],
                            font=(_F, 10), relief="flat", cursor="hand2",
                            anchor="w", padx=14, pady=8,
                            activebackground=C["bg4"],
                            activeforeground=C["text"],
                            command=lambda i=idx: self.notebook.select(i))
            btn.pack(fill="x", pady=2)
            self._nav_btns.append(btn)
            self._tw(btn, bg="bg3", fg="text", hover="bg4")

        self.div2 = tk.Frame(self.sidebar, bg=C["stroke"], height=1)
        self.div2.pack(fill="x", padx=14, pady=6)
        self._tw(self.div2, bg="stroke")

        self.leg_frame = tk.Frame(self.sidebar, bg=C["bg2"])
        self.leg_frame.pack(fill="x", padx=14)
        self._tw(self.leg_frame, bg="bg2")

        self.lbl_moods_hdr = tk.Label(self.leg_frame, text="moods",
                                       bg=C["bg2"], fg=C["text3"], font=(_F, 8))
        self.lbl_moods_hdr.pack(anchor="w", pady=(0, 4))
        self._tw(self.lbl_moods_hdr, bg="bg2", fg="text3")

        for mood, data in me.MOODS.items():
            row = tk.Frame(self.leg_frame, bg=C["bg2"])
            row.pack(fill="x", pady=1)
            self._tw(row, bg="bg2")
            e_lbl = tk.Label(row, text=data["emoji"], bg=C["bg2"], font=(_F, 10))
            e_lbl.pack(side="left")
            self._tw(e_lbl, bg="bg2")
            m_lbl = tk.Label(row, text=mood, bg=C["bg2"], fg=C["text2"],
                              font=(_F, 9))
            m_lbl.pack(side="left", padx=4)
            self._tw(m_lbl, bg="bg2", fg="text2")

    def _stat_pill(self, parent, value, label):
        card = tk.Frame(parent, bg=C["bg3"], padx=10, pady=7)
        card.pack(fill="x", pady=3)
        self._tw(card, bg="bg3")
        v = tk.Label(card, text=value, bg=C["bg3"],
                     fg=C["stat_val"], font=(_F, 18, "bold"))
        v.pack()
        self._tw(v, bg="bg3", fg="stat_val")
        lbl = tk.Label(card, text=label, bg=C["bg3"],
                        fg=C["text2"], font=(_F, 8))
        lbl.pack()
        self._tw(lbl, bg="bg3", fg="text2")
        return v

    # ── Main notebook ──────────────────────────────────────────────────────────
    def _build_main(self):
        self.main_wrap = ttk.Frame(self.root)
        self.main_wrap.grid(row=0, column=1, sticky="nsew")
        self.main_wrap.columnconfigure(0, weight=1)
        self.main_wrap.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.main_wrap)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        self.tab_write     = ttk.Frame(self.notebook)
        self.tab_entries   = ttk.Frame(self.notebook)
        self.tab_analytics = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_write,     text="  write  ")
        self.notebook.add(self.tab_entries,   text="  entries  ")
        self.notebook.add(self.tab_analytics, text="  insights  ")

        self._build_write_tab()
        self._build_entries_tab()
        self._build_analytics_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    # ── Write Tab ──────────────────────────────────────────────────────────────
    def _build_write_tab(self):
        f = self.tab_write
        f.columnconfigure(0, weight=3)
        f.columnconfigure(1, weight=2)
        f.rowconfigure(0, weight=1)

        left = tk.Frame(f, bg=C["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(18, 8), pady=16)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)
        self._tw(left, bg="bg")

        self.lbl_write_date = tk.Label(left,
                                        text=datetime.now().strftime("%A, %d %B %Y"),
                                        bg=C["bg"], fg=C["text2"],
                                        font=(_F, 10, "italic"))
        self.lbl_write_date.grid(row=0, column=0, sticky="w", pady=(0, 2))
        self._tw(self.lbl_write_date, bg="bg", fg="text2")

        self.lbl_write_hdr = tk.Label(left, text="What's on your mind today?",
                                       bg=C["bg"], fg=C["text"],
                                       font=(_F, 18, "bold"))
        self.lbl_write_hdr.grid(row=1, column=0, sticky="w", pady=(0, 10))
        self._tw(self.lbl_write_hdr, bg="bg", fg="text")

        self.entry_title = tk.Entry(left, bg=C["bg2"], fg=C["text"],
                                     font=(_F, 11), relief="flat",
                                     insertbackground=C["accent"],
                                     highlightbackground=C["stroke"],
                                     highlightthickness=1)
        self.entry_title.grid(row=2, column=0, sticky="ew", ipady=7, pady=(0, 8))
        self._tw(self.entry_title, bg="bg2", fg="text", insert="accent",
                  highlight="stroke")
        self._placeholder(self.entry_title, "give this entry a title  (optional)")

        self.text_wrap = tk.Frame(left, bg=C["stroke"], padx=1, pady=1)
        self.text_wrap.grid(row=3, column=0, sticky="nsew")
        self.text_wrap.columnconfigure(0, weight=1)
        self.text_wrap.rowconfigure(0, weight=1)
        self._tw(self.text_wrap, bg="stroke")

        self.text_area = tk.Text(self.text_wrap, bg=C["bg2"], fg=C["text"],
                                  font=(_F, 11), relief="flat",
                                  insertbackground=C["accent"],
                                  wrap="word", padx=16, pady=14,
                                  spacing1=4, spacing2=2, undo=True,
                                  highlightthickness=0)
        self.text_area.grid(row=0, column=0, sticky="nsew")
        self._tw(self.text_area, bg="bg2", fg="text", insert="accent")

        vsb = ttk.Scrollbar(self.text_wrap, orient="vertical",
                             command=self.text_area.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.text_area.configure(yscrollcommand=vsb.set)
        self._placeholder_text(self.text_area,
            "pour your thoughts here...  there's no right or wrong way to write.")

        self.lbl_wc = tk.Label(left, text="", bg=C["bg"], fg=C["text3"],
                                font=(_F, 8, "italic"))
        self.lbl_wc.grid(row=4, column=0, sticky="e", pady=(3, 0))
        self._tw(self.lbl_wc, bg="bg", fg="text3")

        self.entry_tags = tk.Entry(left, bg=C["bg2"], fg=C["text"],
                                    font=(_F, 9), relief="flat",
                                    insertbackground=C["accent"],
                                    highlightbackground=C["stroke"],
                                    highlightthickness=1)
        self.entry_tags.grid(row=5, column=0, sticky="ew", ipady=5, pady=(6, 0))
        self._tw(self.entry_tags, bg="bg2", fg="text", insert="accent",
                  highlight="stroke")
        self._placeholder(self.entry_tags, "tags, separated by commas  (optional)")

        btn_row = tk.Frame(left, bg=C["bg"])
        btn_row.grid(row=6, column=0, sticky="w", pady=(12, 0))
        self._tw(btn_row, bg="bg")

        self.btn_save = tk.Button(btn_row, text="save entry",
                                   bg=C["accent"], fg="white",
                                   font=(_F, 11, "bold"), relief="flat",
                                   cursor="hand2", padx=22, pady=10,
                                   activebackground=C["accent2"],
                                   activeforeground="white",
                                   command=self._save_entry)
        self.btn_save.pack(side="left")
        self._tw(self.btn_save, bg="accent", fg_fixed="white", hover="accent2")

        self.btn_clear = tk.Button(btn_row, text="clear",
                                    bg=C["bg3"], fg=C["text2"],
                                    font=(_F, 10), relief="flat",
                                    cursor="hand2", padx=14, pady=10,
                                    activebackground=C["bg4"],
                                    command=self._clear_editor)
        self.btn_clear.pack(side="left", padx=8)
        self._tw(self.btn_clear, bg="bg3", fg="text2", hover="bg4")

        # Right: Mood Preview
        self.preview_panel = tk.Frame(f, bg=C["bg2"])
        self.preview_panel.grid(row=0, column=1, sticky="nsew",
                                 padx=(0, 18), pady=16)
        self.preview_panel.columnconfigure(0, weight=1)
        self._tw(self.preview_panel, bg="bg2")

        self.lbl_feeling_hdr = tk.Label(self.preview_panel,
                                         text="how you're feeling",
                                         bg=C["bg2"], fg=C["text2"],
                                         font=(_F, 9, "italic"))
        self.lbl_feeling_hdr.pack(pady=(16, 0))
        self._tw(self.lbl_feeling_hdr, bg="bg2", fg="text2")

        self.prev_emoji = tk.Label(self.preview_panel, text="  ",
                                    bg=C["bg2"], fg=C["text"], font=(_F, 54))
        self.prev_emoji.pack(pady=(8, 0))
        self._tw(self.prev_emoji, bg="bg2")

        self.prev_mood = tk.Label(self.preview_panel, text="start writing...",
                                   bg=C["bg2"], fg=C["text2"],
                                   font=(_F, 15, "bold"))
        self.prev_mood.pack()
        self._tw(self.prev_mood, bg="bg2", fg="text2")

        self.prev_conf = tk.Label(self.preview_panel, text="",
                                   bg=C["bg2"], fg=C["text3"],
                                   font=(_F, 8, "italic"))
        self.prev_conf.pack(pady=(2, 10))
        self._tw(self.prev_conf, bg="bg2", fg="text3")

        self.lbl_tone = tk.Label(self.preview_panel, text="emotional tone",
                                  bg=C["bg2"], fg=C["text3"],
                                  font=(_F, 8, "italic"))
        self.lbl_tone.pack(anchor="w", padx=18)
        self._tw(self.lbl_tone, bg="bg2", fg="text3")

        self.val_canvas = tk.Canvas(self.preview_panel, bg=C["bg3"],
                                     height=8, highlightthickness=0)
        self.val_canvas.pack(fill="x", padx=18, pady=(2, 12))
        self._tw(self.val_canvas, bg="bg3")

        self.lbl_top_moods = tk.Label(self.preview_panel,
                                       text="top moods detected",
                                       bg=C["bg2"], fg=C["text3"],
                                       font=(_F, 8, "italic"))
        self.lbl_top_moods.pack(anchor="w", padx=18)
        self._tw(self.lbl_top_moods, bg="bg2", fg="text3")

        self.top_moods_frame = tk.Frame(self.preview_panel, bg=C["bg2"])
        self.top_moods_frame.pack(fill="x", padx=18, pady=(4, 0))
        self._tw(self.top_moods_frame, bg="bg2")

        self.prev_sentiment = tk.Label(self.preview_panel, text="",
                                        bg=C["bg2"], fg=C["accent"],
                                        font=(_F, 9, "italic"))
        self.prev_sentiment.pack(pady=(10, 0))
        self._tw(self.prev_sentiment, bg="bg2")

        self.lbl_quote = tk.Label(self.preview_panel,
                                   text=self._daily_quote(),
                                   bg=C["bg2"], fg=C["text3"],
                                   font=(_F, 8, "italic"),
                                   wraplength=160, justify="center")
        self.lbl_quote.pack(side="bottom", pady=14, padx=12)
        self._tw(self.lbl_quote, bg="bg2", fg="text3")

        self.text_area.bind("<KeyRelease>", self._on_text_key)

    # ── Write helpers ──────────────────────────────────────────────────────────
    def _on_text_key(self, event=None):
        content = self.text_area.get("1.0", "end-1c")
        if content == self._ta_placeholder:
            return
        wc = len(content.split()) if content.strip() else 0
        self.lbl_wc.config(text=f"{wc} word{'s' if wc != 1 else ''}")
        if self._preview_job:
            self.root.after_cancel(self._preview_job)
        self._preview_job = self.root.after(400, self._update_preview)

    def _update_preview(self):
        text = self.text_area.get("1.0", "end-1c")
        if not text.strip() or text == self._ta_placeholder:
            self.prev_emoji.config(text="  ")
            self.prev_mood.config(text="start writing...", fg=C["text2"])
            self.prev_conf.config(text="")
            return

        pred = me.predict_mood(text)
        self.prev_emoji.config(text=pred["emoji"], fg=pred["color"])
        self.prev_mood.config(text=pred["primary_mood"], fg=pred["color"])
        self.prev_conf.config(text=f"{int(pred['confidence']*100)}% confident")

        self.val_canvas.update_idletasks()
        w = self.val_canvas.winfo_width() or 160
        self.val_canvas.delete("all")
        self.val_canvas.create_rectangle(0, 0, w, 8, fill=C["bg3"], outline="")
        mid  = w // 2
        fill = int(pred["valence"] * mid)
        col  = C["accent"] if pred["valence"] >= 0 else C["rose"]
        x0, x1 = (mid, mid+fill) if fill >= 0 else (mid+fill, mid)
        self.val_canvas.create_rectangle(x0, 0, x1, 8, fill=col, outline="")

        for w in self.top_moods_frame.winfo_children():
            w.destroy()
        for mood, score in pred["top_moods"][:4]:
            row = tk.Frame(self.top_moods_frame, bg=C["bg2"])
            row.pack(fill="x", pady=2)
            color = me.MOODS[mood]["color"]
            tk.Label(row, text=f"{me.MOODS[mood]['emoji']} {mood}",
                     bg=C["bg2"], fg=color,
                     font=(_F, 9), width=14, anchor="w").pack(side="left")
            pct = int(score * 100)
            bar = tk.Canvas(row, bg=C["bg3"], height=6, width=90,
                             highlightthickness=0)
            bar.pack(side="left", padx=4)
            bar.update_idletasks()
            bw = bar.winfo_width() or 90
            bar.create_rectangle(0, 0, int(pct/100*bw), 6, fill=color, outline="")
            tk.Label(row, text=f"{pct}%", bg=C["bg2"], fg=C["text3"],
                     font=(_F, 7)).pack(side="left")

        sl   = pred["sentiment_label"]
        scol = C["accent"] if sl == "Positive" else (C["rose"] if sl == "Negative" else C["text2"])
        self.prev_sentiment.config(text=f"overall feeling: {sl.lower()}", fg=scol)

    def _save_entry(self):
        text = self.text_area.get("1.0", "end-1c").strip()
        if not text or text == self._ta_placeholder:
            messagebox.showinfo("nothing yet",
                                "Write something first -- even just a few words.")
            return
        pred  = me.predict_mood(text)
        title = self.entry_title.get().strip()
        if title == self._title_placeholder:
            title = ""
        tags_raw = self.entry_tags.get().strip()
        if tags_raw == self._tags_placeholder:
            tags_raw = ""
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        now  = datetime.now()

        if self._editing_id:
            db.update_entry(self._editing_id, title, text, pred, tags)
            self._editing_id = None
            self.btn_save.config(text="save entry")
            self._toast("entry updated", C["teal"])
        else:
            db.save_entry(now.strftime("%Y-%m-%d"), now.strftime("%H:%M"),
                          title, text, pred, tags)
            self._toast(f"{pred['emoji']}  feeling {pred['primary_mood'].lower()} today",
                        pred["color"])
        self._clear_editor()
        self._load_entries()
        self._refresh_stats()

    def _clear_editor(self):
        self.entry_title.delete(0, "end")
        self._placeholder(self.entry_title, self._title_placeholder)
        self.text_area.delete("1.0", "end")
        self._placeholder_text(self.text_area, self._ta_placeholder)
        self.entry_tags.delete(0, "end")
        self._placeholder(self.entry_tags, self._tags_placeholder)
        self.prev_emoji.config(text="  ")
        self.prev_mood.config(text="start writing...", fg=C["text2"])
        self.prev_conf.config(text="")
        self._editing_id = None
        self.btn_save.config(text="save entry")
        self.lbl_wc.config(text="")

    def _toast(self, message, color=None):
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        bg = color or C["accent"]
        toast.configure(bg=bg)
        x = self.root.winfo_x() + self.root.winfo_width()//2 - 210
        y = self.root.winfo_y() + self.root.winfo_height() - 72
        toast.geometry(f"420x46+{x}+{y}")
        tk.Label(toast, text=f"  {message}", bg=bg, fg="white",
                 font=(_F, 10, "bold")).pack(expand=True)
        toast.after(2600, toast.destroy)

    # ── Placeholders ──────────────────────────────────────────────────────────
    _title_placeholder = "give this entry a title  (optional)"
    _ta_placeholder    = "pour your thoughts here...  there's no right or wrong way to write."
    _tags_placeholder  = "tags, separated by commas  (optional)"

    def _placeholder(self, widget, text):
        widget.delete(0, "end")
        widget.insert(0, text)
        widget.config(fg=C["text3"])
        def on_in(e):
            if widget.get() == text:
                widget.delete(0, "end")
                widget.config(fg=C["text"])
        def on_out(e):
            if not widget.get():
                widget.insert(0, text)
                widget.config(fg=C["text3"])
        widget.bind("<FocusIn>",  on_in)
        widget.bind("<FocusOut>", on_out)

    def _placeholder_text(self, widget, text):
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(fg=C["text3"])
        def on_in(e):
            if widget.get("1.0", "end-1c") == text:
                widget.delete("1.0", "end")
                widget.config(fg=C["text"])
        def on_out(e):
            if not widget.get("1.0", "end-1c").strip():
                widget.insert("1.0", text)
                widget.config(fg=C["text3"])
        widget.bind("<FocusIn>",  on_in)
        widget.bind("<FocusOut>", on_out)

    # ── Entries Tab ────────────────────────────────────────────────────────────
    def _build_entries_tab(self):
        f = self.tab_entries
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        sr = tk.Frame(f, bg=C["bg"])
        sr.grid(row=0, column=0, columnspan=2, sticky="ew", padx=18, pady=(14, 6))
        self._tw(sr, bg="bg")

        self.lbl_search = tk.Label(sr, text="search", bg=C["bg"],
                                    fg=C["text2"], font=(_F, 9, "italic"))
        self.lbl_search.pack(side="left")
        self._tw(self.lbl_search, bg="bg", fg="text2")

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._load_entries())
        self.search_entry = tk.Entry(sr, textvariable=self.search_var,
                                      bg=C["bg2"], fg=C["text"],
                                      font=(_F, 10), relief="flat",
                                      insertbackground=C["accent"],
                                      highlightbackground=C["stroke"],
                                      highlightthickness=1)
        self.search_entry.pack(side="left", fill="x", expand=True,
                                ipady=5, padx=(8, 0))
        self._tw(self.search_entry, bg="bg2", fg="text", insert="accent",
                  highlight="stroke")

        cols = ("date", "mood", "title", "words")
        self.tree = ttk.Treeview(f, columns=cols, show="headings",
                                  selectmode="browse")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=18, pady=4)
        f.rowconfigure(1, weight=1)
        for col, hdr, w, anc in [
            ("date",  "date",    100, "center"),
            ("mood",  "feeling", 130, "center"),
            ("title", "title",   280, "w"),
            ("words", "words",    70, "center"),
        ]:
            self.tree.heading(col, text=hdr)
            self.tree.column(col, width=w, anchor=anc)

        vsb = ttk.Scrollbar(f, orient="vertical", command=self.tree.yview)
        vsb.grid(row=1, column=1, sticky="ns", pady=4)
        self.tree.configure(yscrollcommand=vsb.set)

        self.det_frame = tk.Frame(f, bg=C["bg2"])
        self.det_frame.grid(row=2, column=0, columnspan=2, sticky="ew",
                             padx=18, pady=(4, 12))
        self.det_frame.columnconfigure(0, weight=1)
        self._tw(self.det_frame, bg="bg2")

        self.detail_text = tk.Text(self.det_frame, bg=C["bg2"], fg=C["text"],
                                    font=(_F, 10), height=5, relief="flat",
                                    wrap="word", padx=14, pady=10,
                                    state="disabled", highlightthickness=0)
        self.detail_text.grid(row=0, column=0, sticky="ew")
        self._tw(self.detail_text, bg="bg2", fg="text")

        br = tk.Frame(self.det_frame, bg=C["bg2"])
        br.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self._tw(br, bg="bg2")

        self.btn_edit = tk.Button(br, text="edit",
                                   bg=C["teal"], fg="white",
                                   font=(_F, 9), relief="flat", cursor="hand2",
                                   padx=14, pady=5, command=self._edit_selected)
        self.btn_edit.pack(side="left", padx=(0, 6))
        self._tw(self.btn_edit, bg="teal", fg_fixed="white")

        self.btn_del = tk.Button(br, text="delete",
                                  bg=C["rose2"], fg="white",
                                  font=(_F, 9), relief="flat", cursor="hand2",
                                  padx=14, pady=5, command=self._delete_selected)
        self.btn_del.pack(side="left")
        self._tw(self.btn_del, bg="rose2", fg_fixed="white")

        self.tree.bind("<<TreeviewSelect>>", self._on_entry_select)

    def _load_entries(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        q = self.search_var.get().strip() if hasattr(self, "search_var") else ""
        entries = db.search_entries(q) if q else db.get_all_entries()
        for e in entries:
            mood  = e["primary_mood"]
            emoji = me.MOODS.get(mood, {}).get("emoji", "")
            color = me.MOODS.get(mood, {}).get("color", C["text2"])
            title = e.get("title") or "(untitled)"
            self.tree.insert("", "end", iid=str(e["id"]),
                              values=(e["date"], f"{emoji}  {mood}",
                                      title, e.get("word_count", 0)),
                              tags=(mood,))
            self.tree.tag_configure(mood, foreground=color)

    def _on_entry_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        entry = db.get_entry_by_id(int(sel[0]))
        if not entry:
            return
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        mood  = entry["primary_mood"]
        emoji = me.MOODS.get(mood, {}).get("emoji", "")
        hdr   = f"{emoji}  {mood}   ·   {entry['date']}  {entry['time']}"
        if entry.get("title"):
            hdr = f"{entry['title']}  --  " + hdr
        self.detail_text.insert("end", hdr + "\n\n", "hdr")
        self.detail_text.insert("end", entry["content"])
        self.detail_text.tag_config("hdr", foreground=C["accent"],
                                     font=(_F, 10, "bold"))
        self.detail_text.config(state="disabled")

    def _edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        entry = db.get_entry_by_id(int(sel[0]))
        if not entry:
            return
        self._editing_id = entry["id"]
        self.entry_title.config(fg=C["text"])
        self.entry_title.delete(0, "end")
        if entry.get("title"):
            self.entry_title.insert(0, entry["title"])
        self.text_area.config(fg=C["text"])
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", entry["content"])
        if entry.get("tags"):
            self.entry_tags.config(fg=C["text"])
            self.entry_tags.delete(0, "end")
            self.entry_tags.insert(0, entry["tags"])
        self.btn_save.config(text="update entry")
        self.notebook.select(0)
        self._update_preview()

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        if messagebox.askyesno("are you sure?",
                               "This will permanently remove this entry."):
            db.delete_entry(int(sel[0]))
            self._load_entries()
            self._refresh_stats()

    # ── Analytics Tab ──────────────────────────────────────────────────────────
    def _build_analytics_tab(self):
        f = self.tab_analytics
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        self.ctrl_frame = tk.Frame(f, bg=C["bg"])
        self.ctrl_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 6))
        self._tw(self.ctrl_frame, bg="bg")

        self.lbl_view = tk.Label(self.ctrl_frame, text="view:", bg=C["bg"],
                                  fg=C["text2"], font=(_F, 9, "italic"))
        self.lbl_view.pack(side="left")
        self._tw(self.lbl_view, bg="bg", fg="text2")

        self.chart_var = tk.StringVar(value="mood distribution")
        self.chart_menu = ttk.Combobox(self.ctrl_frame,
                                        textvariable=self.chart_var,
                                        values=["mood distribution",
                                                "emotional journey",
                                                "day map",
                                                "emotion shape",
                                                "best days",
                                                "writing volume",
                                                "mood landscape",
                                                "mood flow"],
                                        state="readonly", width=22)
        self.chart_menu.pack(side="left", padx=8)

        self.lbl_period = tk.Label(self.ctrl_frame, text="period:", bg=C["bg"],
                                    fg=C["text2"], font=(_F, 9, "italic"))
        self.lbl_period.pack(side="left")
        self._tw(self.lbl_period, bg="bg", fg="text2")

        self.period_var = tk.StringVar(value="30 days")
        self.period_menu = ttk.Combobox(self.ctrl_frame,
                                         textvariable=self.period_var,
                                         values=["7 days","14 days","30 days",
                                                  "60 days","90 days","all time"],
                                         state="readonly", width=10)
        self.period_menu.pack(side="left", padx=8)

        self.btn_refresh = tk.Button(self.ctrl_frame, text="refresh",
                                      bg=C["teal"], fg="white",
                                      font=(_F, 9), relief="flat",
                                      cursor="hand2", padx=14, pady=5,
                                      command=self._render_chart)
        self.btn_refresh.pack(side="left", padx=6)
        self._tw(self.btn_refresh, bg="teal", fg_fixed="white")

        self.chart_frame = tk.Frame(f, bg=C["bg"])
        self.chart_frame.grid(row=1, column=0, sticky="nsew",
                               padx=18, pady=(0, 12))
        self.chart_frame.columnconfigure(0, weight=1)
        self.chart_frame.rowconfigure(0, weight=1)
        self._tw(self.chart_frame, bg="bg")

        self.chart_menu.bind("<<ComboboxSelected>>", lambda e: self._render_chart())

    def _on_tab_change(self, event):
        if self.notebook.index(self.notebook.select()) == 2:
            self._render_chart()

    def _render_chart(self):
        name   = self.chart_var.get()
        period = self.period_var.get()
        days   = 36500 if period == "all time" else int(period.split()[0])

        for w in self.chart_frame.winfo_children():
            w.destroy()
        self._chart_widget = None

        loading = tk.Label(self.chart_frame, text="drawing...",
                            bg=C["bg"], fg=C["text2"], font=(_F, 11, "italic"))
        loading.pack(expand=True)
        self._tw(loading, bg="bg", fg="text2")
        self.root.update_idletasks()

        def _do():
            from datetime import timedelta
            all_e   = db.get_all_entries(limit=5000)
            cutoff  = (date.today() - timedelta(days=days)).isoformat()
            entries = [e for e in all_e if e["date"] >= cutoff] if days < 36500 else all_e
            dark    = self._dark_mode

            chart_map = {
                "mood distribution": lambda: charts.mood_donut(entries, dark=dark),
                "emotional journey": lambda: charts.valence_timeline(
                                         db.get_valence_timeline(days=days), dark=dark),
                "day map":           lambda: charts.mood_heatmap(entries,
                                         days=min(days, 90), dark=dark),
                "emotion shape":     lambda: charts.valence_arousal_scatter(entries, dark=dark),
                "best days":         lambda: charts.weekday_mood_bar(
                                         db.get_mood_by_weekday(days=days), dark=dark),
                "writing volume":    lambda: charts.word_count_trend(
                                         db.get_word_count_trend(days=days), dark=dark),
                "mood landscape":    lambda: charts.mood_radar(entries, dark=dark),
                "mood flow":         lambda: charts.mood_transition(entries, dark=dark),
            }

            fig = chart_map.get(name, lambda: None)()
            try:
                loading.destroy()
            except Exception:
                pass
            if fig:
                canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
                self._chart_widget = canvas
                plt.close(fig)

        self.root.after(40, _do)

    # ── Stats ──────────────────────────────────────────────────────────────────
    def _refresh_stats(self):
        total  = db.get_total_entries()
        streak = db.get_streak()
        counts = db.get_mood_counts(days=30)
        top    = max(counts, key=counts.get) if counts else "--"
        emoji  = me.MOODS.get(top, {}).get("emoji", "") if top != "--" else ""
        self.lbl_total.config(text=str(total))
        self.lbl_streak.config(text=str(streak))
        self.lbl_top.config(text=f"{emoji} {top}" if top != "--" else "--",
                             font=(_F, 12, "bold"))

    # ── Daily quote ────────────────────────────────────────────────────────────
    def _daily_quote(self):
        quotes = [
            'the act of writing is the act of discovering what you believe.',
            'fill your paper with the breathings of your heart.',
            "journaling is like whispering to one's self.",
            'write it on your heart that every day is the best day.',
            'in the journal I am at ease.',
            'your story matters -- even the quiet parts.',
            'one day or day one. you decide.',
        ]
        import hashlib
        day_hash = int(hashlib.md5(str(date.today()).encode()).hexdigest(), 16)
        return quotes[day_hash % len(quotes)]

    # ── Theme toggle ───────────────────────────────────────────────────────────
    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        C.update(THEMES["dark" if self._dark_mode else "light"])
        self.btn_theme.config(text="☀️" if self._dark_mode else "🌙")
        self.root.configure(bg=C["bg"])
        self._apply_ttk_styles()
        self._repaint_all()
        if self.notebook.index(self.notebook.select()) == 2:
            self._render_chart()

    def _repaint_all(self):
        for widget, props in self._themed_widgets:
            try:
                cfg = {}
                if "bg"       in props: cfg["background"]      = C[props["bg"]]
                if "fg"       in props: cfg["foreground"]      = C[props["fg"]]
                if "fg_fixed" in props: cfg["foreground"]      = props["fg_fixed"]
                if "insert"   in props: cfg["insertbackground"] = C[props["insert"]]
                if "highlight"in props: cfg["highlightbackground"] = C[props["highlight"]]
                if cfg:
                    widget.config(**cfg)
                if "hover" in props and isinstance(widget, tk.Button):
                    hk = props["hover"]
                    bk = props.get("bg", "bg3")
                    widget.config(activebackground=C[hk])
                    widget.bind("<Enter>", lambda e, w=widget, k=hk: w.config(bg=C[k]))
                    widget.bind("<Leave>", lambda e, w=widget, k=bk: w.config(bg=C[k]))
            except tk.TclError:
                pass
        try:
            self.detail_text.tag_config("hdr", foreground=C["accent"])
        except Exception:
            pass

    def _tw(self, widget, bg=None, fg=None, fg_fixed=None,
             insert=None, highlight=None, hover=None):
        props = {}
        if bg:         props["bg"]         = bg
        if fg:         props["fg"]         = fg
        if fg_fixed:   props["fg_fixed"]   = fg_fixed
        if insert:     props["insert"]     = insert
        if highlight:  props["highlight"]  = highlight
        if hover:      props["hover"]      = hover
        self._themed_widgets.append((widget, props))
        if hover and isinstance(widget, tk.Button):
            widget.bind("<Enter>", lambda e, w=widget, k=hover: w.config(bg=C[k]))
            widget.bind("<Leave>", lambda e, w=widget, k=bg:    w.config(bg=C[k]))

    def run(self):
        self.root.mainloop()
