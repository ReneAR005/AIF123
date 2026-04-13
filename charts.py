"""
charts.py — Soft journalling-aesthetic charts with light/dark theme support.
Every chart function accepts dark=False/True to switch palettes.
"""

import math
from datetime import date, timedelta
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from mood_engine import MOODS

# ── Palettes ───────────────────────────────────────────────────────────────────
_LIGHT = dict(
    BG="#FAF7F2", BG2="#F3EDE3", BG3="#EDE5D8",
    STROKE="#D9CEBB", TEXT="#5C4F3D", TEXT2="#9B8B78",
    ACCENT="#8BAF8B", ROSE="#C9808A", LAVEND="#B5A8CE", TEAL="#7BAF9E",
)
_DARK = dict(
    BG="#16121F", BG2="#1E1830", BG3="#261F3D",
    STROKE="#3A3055", TEXT="#E8E2F5", TEXT2="#9F94C0",
    ACCENT="#9B7FD4", ROSE="#C47A9A", LAVEND="#A890D0", TEAL="#7A9EC4",
)

def _P(dark=False):
    return _DARK if dark else _LIGHT


def _apply_style(fig, axes, dark=False):
    p = _P(dark)
    fig.patch.set_facecolor(p["BG"])
    if not isinstance(axes, (list, tuple)):
        axes = [axes]
    for ax in axes:
        ax.set_facecolor(p["BG2"])
        ax.tick_params(colors=p["TEXT2"], labelsize=9, length=0)
        ax.xaxis.label.set_color(p["TEXT2"])
        ax.yaxis.label.set_color(p["TEXT2"])
        ax.title.set_color(p["TEXT"])
        for spine in ax.spines.values():
            spine.set_color(p["STROKE"])
            spine.set_linewidth(0.8)
        ax.grid(color=p["STROKE"], linewidth=0.5, alpha=0.6, linestyle="--")


def _mood_color(mood):
    return MOODS.get(mood, {}).get("color", "#A89BAE")


def _pastel(hex_color, mix=0.35):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    r = int(r + (255 - r) * mix)
    g = int(g + (255 - g) * mix)
    b = int(b + (255 - b) * mix)
    return f"#{r:02X}{g:02X}{b:02X}"


def _empty_chart(msg, dark=False):
    p = _P(dark)
    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor(p["BG"])
    ax.set_facecolor(p["BG"])
    ax.axis("off")
    ax.text(0.5, 0.5, msg, ha="center", va="center",
            fontsize=13, color=p["TEXT2"], transform=ax.transAxes,
            fontstyle="italic", fontfamily="serif", linespacing=1.8)
    return fig


# ── 1. Mood Donut ──────────────────────────────────────────────────────────────
def mood_donut(entries, dark=False):
    if not entries:
        return _empty_chart("No entries yet —\nstart writing", dark=dark)

    p = _P(dark)
    counts = Counter(e["primary_mood"] for e in entries)
    moods  = list(counts.keys())
    values = list(counts.values())
    mix    = 0.25 if dark else 0.35
    colors = [_pastel(_mood_color(m), mix) for m in moods]

    fig, ax = plt.subplots(figsize=(7, 5.5))
    fig.patch.set_facecolor(p["BG"])
    ax.set_facecolor(p["BG"])

    _, _, autotexts = ax.pie(
        values, labels=None, colors=colors,
        autopct="%1.0f%%", pctdistance=0.78, startangle=90,
        wedgeprops={"width": 0.52, "edgecolor": p["BG"], "linewidth": 3},
    )
    for t in autotexts:
        t.set_color(p["TEXT"])
        t.set_fontsize(8.5)

    total = sum(values)
    ax.text(0, 0.1, str(total), ha="center", va="center",
            fontsize=28, color=p["TEXT"], fontweight="bold", fontfamily="serif")
    ax.text(0, -0.18, "entries", ha="center", fontsize=10,
            color=p["TEXT2"], fontstyle="italic", fontfamily="serif")

    handles = [
        mpatches.Patch(facecolor=colors[i], edgecolor=_mood_color(moods[i]),
                       linewidth=1.5,
                       label=f"{MOODS[moods[i]]['emoji']}  {moods[i]}  ({values[i]})")
        for i in range(len(moods))
    ]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.02, 0.5),
              frameon=False, labelcolor=p["TEXT"], fontsize=9, labelspacing=0.8)
    ax.set_title("how you've been feeling", fontsize=13, color=p["TEXT"],
                 pad=16, fontstyle="italic", fontfamily="serif")
    fig.tight_layout()
    return fig


# ── 2. Valence Timeline ────────────────────────────────────────────────────────
def valence_timeline(rows, dark=False):
    if not rows:
        return _empty_chart("No timeline data yet.", dark=dark)

    p = _P(dark)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    _apply_style(fig, ax, dark)

    dates    = [r["date"] for r in rows]
    valences = [r["avg_valence"] for r in rows]
    x = range(len(dates))

    ax.fill_between(x, valences, 0, where=[v >= 0 for v in valences],
                    color=p["ACCENT"], alpha=0.25, interpolate=True)
    ax.fill_between(x, valences, 0, where=[v < 0 for v in valences],
                    color=p["ROSE"], alpha=0.25, interpolate=True)
    ax.plot(x, valences, color=p["TEAL"], linewidth=2, zorder=3, alpha=0.9)
    ax.scatter(x, valences, color=p["BG"], s=50, zorder=5,
               edgecolors=p["TEAL"], linewidth=1.8)
    ax.axhline(0, color=p["STROKE"], linewidth=1, linestyle="--", alpha=0.8)

    step = max(1, len(dates) // 10)
    ax.set_xticks(list(x)[::step])
    ax.set_xticklabels(dates[::step], rotation=30, ha="right", fontsize=8)
    ax.set_ylim(-1.15, 1.15)
    ax.set_ylabel("feeling", fontsize=9, fontstyle="italic")
    ax.text(0.01, 0.93, "brighter", transform=ax.transAxes,
            color=p["ACCENT"], fontsize=8, va="top", fontstyle="italic")
    ax.text(0.01, 0.07, "heavier", transform=ax.transAxes,
            color=p["ROSE"], fontsize=8, fontstyle="italic")
    ax.set_title("your emotional journey", fontsize=13, color=p["TEXT"],
                 pad=12, fontstyle="italic", fontfamily="serif")
    fig.tight_layout()
    return fig


# ── 3. Mood Heatmap ────────────────────────────────────────────────────────────
def mood_heatmap(entries, days=60, dark=False):
    if not entries:
        return _empty_chart("No data for the heatmap yet.", dark=dark)

    p = _P(dark)
    from collections import defaultdict
    dv = defaultdict(list)
    for e in entries:
        dv[e["date"]].append(e["valence"])
    date_val = {d: sum(vs)/len(vs) for d, vs in dv.items()}

    today     = date.today()
    all_dates = [today - timedelta(days=i) for i in range(days-1, -1, -1)]
    start     = all_dates[0]
    pad       = start.weekday()
    grid_dates = [start - timedelta(days=pad-i) for i in range(pad-1, -1, -1)] + all_dates
    weeks     = math.ceil(len(grid_dates) / 7)
    while len(grid_dates) < weeks * 7:
        grid_dates.append(None)

    matrix = np.full((7, weeks), np.nan)
    for i, d in enumerate(grid_dates):
        col, row = divmod(i, 7)
        if d is not None:
            matrix[row, col] = date_val.get(d.isoformat(), np.nan)

    fig, ax = plt.subplots(figsize=(min(14, weeks * 0.9 + 2), 3.2))
    fig.patch.set_facecolor(p["BG"])
    ax.set_facecolor(p["BG"])

    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "journal", [p["ROSE"], p["BG3"], p["ACCENT"]], N=256
    )
    cmap.set_bad(color=p["BG3"])

    im = ax.imshow(matrix, cmap=cmap, vmin=-1, vmax=1,
                   aspect="auto", interpolation="nearest")
    ax.set_yticks(range(7))
    ax.set_yticklabels(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],
                        fontsize=8, color=p["TEXT2"])
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    cbar = fig.colorbar(im, ax=ax, orientation="vertical",
                         fraction=0.025, pad=0.02)
    cbar.ax.tick_params(colors=p["TEXT2"], labelsize=7, length=0)
    cbar.set_label("lighter = brighter", color=p["TEXT2"],
                    fontsize=7, fontstyle="italic")
    cbar.outline.set_edgecolor(p["STROKE"])

    ax.set_title("a map of your days", fontsize=13, color=p["TEXT"],
                 pad=10, fontstyle="italic", fontfamily="serif")
    fig.tight_layout()
    return fig


# ── 4. Emotion Circumplex ──────────────────────────────────────────────────────
def valence_arousal_scatter(entries, dark=False):
    if not entries:
        return _empty_chart("No entries yet.", dark=dark)

    p = _P(dark)
    fig, ax = plt.subplots(figsize=(6.5, 6))
    _apply_style(fig, ax, dark)

    ax.axhline(0, color=p["STROKE"], linewidth=1, linestyle="--")
    ax.axvline(0, color=p["STROKE"], linewidth=1, linestyle="--")

    for txt, xy, ha in [
        ("light & energised", ( 0.6,  0.9), "center"),
        ("tense & activated", (-0.9,  0.9), "left"),
        ("soft & resting",    ( 0.6, -0.9), "center"),
        ("heavy & low",       (-0.9, -0.9), "left"),
    ]:
        ax.text(xy[0], xy[1], txt, fontsize=7.5, color=p["TEXT2"],
                ha=ha, fontstyle="italic")

    mood_groups = {}
    for e in entries:
        m = e["primary_mood"]
        if m not in mood_groups:
            mood_groups[m] = {"v":[], "a":[], "color": _mood_color(m)}
        mood_groups[m]["v"].append(e["valence"])
        mood_groups[m]["a"].append(e["arousal"])

    handles = []
    for mood, data in mood_groups.items():
        col = data["color"]
        ax.scatter(data["v"], data["a"],
                   color=_pastel(col, 0.2 if dark else 0.3),
                   edgecolors=col, linewidths=1.2, alpha=0.8, s=55)
        handles.append(mpatches.Patch(
            facecolor=_pastel(col, 0.2 if dark else 0.3),
            edgecolor=col, linewidth=1.2,
            label=f"{MOODS[mood]['emoji']} {mood}"))

    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_xlabel("valence  ( heavier <- -> lighter )", fontsize=8, fontstyle="italic")
    ax.set_ylabel("energy  ( calm <-> active )", fontsize=8, fontstyle="italic")
    ax.set_title("the shape of your emotions", fontsize=13, color=p["TEXT"],
                 pad=12, fontstyle="italic", fontfamily="serif")
    ax.legend(handles=handles, loc="upper left", frameon=True, labelcolor=p["TEXT"],
              fontsize=8, ncol=2, facecolor=p["BG"], edgecolor=p["STROKE"])
    fig.tight_layout()
    return fig


# ── 5. Weekday Bars ────────────────────────────────────────────────────────────
def weekday_mood_bar(weekday_data, dark=False):
    p = _P(dark)
    days_order = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    vals = [weekday_data.get(d, 0) for d in days_order]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    _apply_style(fig, ax, dark)

    mix    = 0.2 if dark else 0.3
    colors = [_pastel(p["ACCENT"], mix) if v >= 0 else _pastel(p["ROSE"], mix)
              for v in vals]
    edges  = [p["ACCENT"] if v >= 0 else p["ROSE"] for v in vals]

    bars = ax.bar(days_order, vals, color=colors, edgecolor=edges,
                  linewidth=1.2, width=0.55)
    for bar, val in zip(bars, vals):
        if val != 0:
            ax.text(bar.get_x() + bar.get_width()/2,
                    val + (0.04 if val >= 0 else -0.07),
                    f"{val:.2f}", ha="center", fontsize=8,
                    color=p["TEXT2"], fontstyle="italic")

    ax.axhline(0, color=p["STROKE"], linewidth=1, linestyle="--")
    ax.set_ylim(-1.15, 1.15)
    ax.set_ylabel("average feeling", fontsize=9, fontstyle="italic")
    ax.set_title("your best & hardest days", fontsize=13, color=p["TEXT"],
                 pad=12, fontstyle="italic", fontfamily="serif")
    fig.tight_layout()
    return fig


# ── 6. Writing Volume ──────────────────────────────────────────────────────────
def word_count_trend(rows, dark=False):
    if not rows:
        return _empty_chart("No writing data yet.", dark=dark)

    p = _P(dark)
    fig, ax = plt.subplots(figsize=(9, 4))
    _apply_style(fig, ax, dark)

    dates = [r["date"] for r in rows]
    words = [r["total_words"] for r in rows]
    x = range(len(dates))

    ax.fill_between(x, words, 0, color=p["LAVEND"], alpha=0.3)
    ax.plot(x, words, color=p["LAVEND"], linewidth=2, alpha=0.9)
    ax.scatter(x, words, color=p["BG"], s=40, zorder=3,
               edgecolors=p["LAVEND"], linewidth=1.8)

    step = max(1, len(dates)//10)
    ax.set_xticks(list(x)[::step])
    ax.set_xticklabels(dates[::step], rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("words", fontsize=9, fontstyle="italic")
    ax.set_title("how much you've poured out", fontsize=13, color=p["TEXT"],
                 pad=12, fontstyle="italic", fontfamily="serif")
    fig.tight_layout()
    return fig


# ── 7. Mood Radar ──────────────────────────────────────────────────────────────
def mood_radar(entries, dark=False):
    if not entries:
        return _empty_chart("No entries yet.", dark=dark)

    p = _P(dark)
    from mood_engine import get_all_moods
    moods  = get_all_moods()
    counts = Counter(e["primary_mood"] for e in entries)
    values = [counts.get(m, 0) for m in moods]
    total  = max(sum(values), 1)
    vn     = [v/total for v in values]

    N      = len(moods)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    vn    += vn[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6.5, 6.5), subplot_kw={"polar": True})
    fig.patch.set_facecolor(p["BG"])
    ax.set_facecolor(p["BG2"])

    ax.plot(angles, vn, color=p["TEAL"], linewidth=1.8, alpha=0.9)
    ax.fill(angles, vn, color=p["TEAL"], alpha=0.18)

    ax.set_thetagrids(
        np.degrees(angles[:-1]),
        [f"{MOODS[m]['emoji']} {m}" for m in moods],
        color=p["TEXT"], fontsize=9,
    )
    ax.set_yticklabels([])
    ax.grid(color=p["STROKE"], linewidth=0.6)
    ax.spines["polar"].set_color(p["STROKE"])
    ax.tick_params(colors=p["TEXT2"])

    ax.set_title("your emotional landscape", fontsize=13, color=p["TEXT"],
                 pad=22, fontstyle="italic", fontfamily="serif")
    fig.tight_layout()
    return fig


# ── 8. Mood Transitions ────────────────────────────────────────────────────────
def mood_transition(entries, dark=False):
    if len(entries) < 2:
        return _empty_chart("Need at least 2 entries\nto see transitions.", dark=dark)

    p = _P(dark)
    sorted_e = sorted(entries, key=lambda e: (e["date"], e["time"]))
    transitions = Counter()
    for i in range(len(sorted_e)-1):
        a = sorted_e[i]["primary_mood"]
        b = sorted_e[i+1]["primary_mood"]
        transitions[(a, b)] += 1

    top    = transitions.most_common(10)
    labels = [f"{MOODS[a]['emoji']} {a}  ->  {MOODS[b]['emoji']} {b}" for (a,b),_ in top]
    counts = [c for _, c in top]
    mix    = 0.2 if dark else 0.3
    colors = [_pastel(_mood_color(b), mix) for (_,b),_ in top]
    edges  = [_mood_color(b) for (_,b),_ in top]

    fig, ax = plt.subplots(figsize=(9, 5))
    _apply_style(fig, ax, dark)

    y = range(len(labels))
    ax.barh(list(y), counts, color=colors, edgecolor=edges,
            linewidth=1.1, height=0.6)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9, color=p["TEXT"])
    ax.set_xlabel("times", fontsize=9, fontstyle="italic")
    ax.set_title("how your moods flow into each other", fontsize=13,
                 color=p["TEXT"], pad=12, fontstyle="italic", fontfamily="serif")
    ax.invert_yaxis()
    ax.grid(axis="x", color=p["STROKE"], linewidth=0.5, linestyle="--")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig
