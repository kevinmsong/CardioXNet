"""Generate publication-ready manuscript figures from benchmark outputs.

Figures use the color-vision-deficiency-safe Okabe-Ito palette, redundant
patterns or markers wherever color carries meaning, regular sans-serif text,
embedded TrueType fonts in vector output, and a 600 dpi PNG companion.

Usage:
    python bench/make_figures.py --manifest bench/out/manifest.json \
        --holdout bench/out/holdout.json --out paper
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Okabe-Ito palette. Color is always reinforced by a label, hatch, or marker.
BLUE = "#0072B2"
ORANGE = "#E69F00"
SKY = "#56B4E9"
GREEN = "#009E73"
YELLOW = "#F0E442"
VERMILLION = "#D55E00"
PURPLE = "#CC79A7"
TEAL, ACCENT_SOFT = GREEN, "#F2FAF7"
INK, INK_2, MUTED = "#111111", "#4C4C4C", "#7A7A72"
SURFACE = "#ffffff"
GRID = "#e4e3de"

TIER_ORDER = [
    "Highly Novel", "Novel", "Emerging", "Established", "Unverified", "Ungrounded"
]
TIER_COLOR = {
    "Highly Novel": BLUE,
    "Novel": GREEN,
    "Emerging": ORANGE,
    "Established": MUTED,
    # The query was measured, but a required prerequisite did not support a
    # literature-novelty interpretation.
    "Unverified": PURPLE,
    # Not a weak result but an undefined one: the seed genes have too little
    # disease literature for any novelty call to mean anything.
    "Ungrounded": VERMILLION,
}
TIER_HATCH = {
    "Highly Novel": "////",
    "Novel": "\\\\",
    "Emerging": "....",
    "Established": "xx",
    "Unverified": "oo",
    "Ungrounded": "++++",
}
TIER_MARKER = {
    "Highly Novel": "o",
    "Novel": "s",
    "Emerging": "^",
    "Established": "D",
    "Unverified": "P",
    "Ungrounded": "X",
}


def style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.weight": "normal",
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.titleweight": "normal",
        "axes.labelsize": 8,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK_2,
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        "legend.frameon": False,
        "legend.fontsize": 7.5,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def despine(ax, keep=("left", "bottom")) -> None:
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in keep)


def save(fig, out_dir: Path, name: str, *, tight: bool = True) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        kwargs = {"dpi": 600, "facecolor": SURFACE}
        if tight:
            kwargs["bbox_inches"] = "tight"
        fig.savefig(out_dir / f"{name}.{ext}", **kwargs)
    plt.close(fig)
    print(f"  wrote {name}.pdf / .png")


def spearman(xs: List[float], ys: List[float]) -> Optional[float]:
    """Spearman rank correlation with average ranks for ties."""
    if len(xs) != len(ys) or len(xs) < 3:
        return None

    def ranks(values: List[float]) -> List[float]:
        order = sorted(range(len(values)), key=values.__getitem__)
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = rank
            i = j + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    numerator = sum((x - mx) * (y - my) for x, y in zip(rx, ry))
    denominator = math.sqrt(
        sum((x - mx) ** 2 for x in rx) * sum((y - my) ** 2 for y in ry)
    )
    return numerator / denominator if denominator else None


def load_report(run_json: Path) -> Optional[dict]:
    """Resolve a bench run to the report dict holding ranked_hypotheses."""
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    files = payload.get("report_files") or {}
    report_path = files.get("json")
    if report_path and Path(report_path).exists():
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
        report["_bench"] = payload.get("_bench", {})
        report["_results"] = payload.get("results", {})
        return report
    return None


# --------------------------------------------------------------------------
# Figure 1 -- complete analysis workflow
# --------------------------------------------------------------------------
def fig_workflow(out_dir: Path) -> None:
    """Show the complete evidence flow, safeguards, score, and audit output."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    stages = [
        ("1", "Input panel", "Validated genes\nand disease context"),
        ("2", "Network expansion", "High-confidence\nSTRING v12 partners"),
        ("3", "Primary enrichment", "Reactome, KEGG,\nWikiPathways, GO:BP"),
        ("4", "Secondary expansion", "Member genes with optional\nliterature augmentation"),
        (
            "5",
            "PPS and annotations",
            "Base: significance, effect,\n"
            "specificity, upstream support,\n"
            "and database weight\n"
            "Final: bounded semantic relevance\n"
            "multiplier. Separate annotations:\n"
            "empirical q, GTEx, druggability",
        ),
        ("6", "Grounding checks", "Seed-disease records at least 100;\nconcept verification at least 20"),
        ("7", "Composite novelty", "Pathway × seeds × disease;\nlow seed overlap (2:1)"),
        ("8", "Discovery ranking", "PPS × composite novelty;\noperational literature tier"),
        ("9", "Auditable output", "Lineage, statistics, queries,\nrun metadata, and export"),
    ]
    fig, ax = plt.subplots(figsize=(7.35, 4.55))
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 3)
    ax.axis("off")

    # Serpentine reading order avoids crossing arrows while preserving the
    # actual computation order.
    positions = [
        (0.03, 2.08), (1.03, 2.08), (2.03, 2.08),
        (2.03, 1.13), (1.03, 1.13), (0.03, 1.13),
        (0.03, 0.18), (1.03, 0.18), (2.03, 0.18),
    ]
    for index, ((number, title, detail), (x, y)) in enumerate(zip(stages, positions)):
        safeguarded = index >= 5
        face = ACCENT_SOFT if safeguarded else SURFACE
        edge = TEAL if safeguarded else GRID
        box = FancyBboxPatch(
            (x, y), 0.87, 0.65,
            boxstyle="round,pad=0.025,rounding_size=0.045",
            linewidth=1.1, edgecolor=edge, facecolor=face,
        )
        ax.add_patch(box)
        ax.text(x + 0.07, y + 0.51, number, color=TEAL, fontsize=8,
                weight="normal", ha="left", va="center")
        ax.text(x + 0.18, y + 0.51, title, color=INK, fontsize=7.6,
                weight="normal", ha="left", va="center")
        ax.text(x + 0.07, y + 0.24, detail, color=INK_2, fontsize=6.65,
                ha="left", va="center", linespacing=1.18)

    arrows = [
        ((0.91, 2.405), (1.02, 2.405)),
        ((1.91, 2.405), (2.02, 2.405)),
        ((2.465, 2.07), (2.465, 1.82)),
        ((2.02, 1.455), (1.91, 1.455)),
        ((1.02, 1.455), (0.91, 1.455)),
        ((0.465, 1.12), (0.465, 0.87)),
        ((0.91, 0.505), (1.02, 0.505)),
        ((1.91, 0.505), (2.02, 0.505)),
    ]
    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>",
                                     mutation_scale=10, linewidth=1,
                                     color=MUTED))

    ax.text(0.03, 2.88,
            "Evidence flow from a focused gene panel to a bounded, auditable literature-gap hypothesis",
            color=INK, fontsize=9.5, weight="normal", ha="left")
    ax.text(0.03, 0.035,
            "Safeguards distinguish a verified exact-query gap from missing seed grounding, ambiguous pathway terminology, "
            "or a failed external measurement.",
            color=MUTED, fontsize=6.7, ha="left")
    save(fig, out_dir, "fig1_cardioxnet_workflow")


# --------------------------------------------------------------------------
# Figure 6 -- key application views
# --------------------------------------------------------------------------
def fig_interface(out_dir: Path) -> None:
    """Render two tightly cropped scientific application views."""
    root = Path(__file__).resolve().parents[1]
    images = [
        root / "docs" / "screenshots" / "10-manuscript-ranked-results.png",
        root / "docs" / "screenshots" / "11-manuscript-pathway-evidence.png",
    ]
    if not all(path.exists() for path in images):
        print("  ! manuscript UI screenshots not found, skipping fig6")
        return

    outputs = [
        (images[0], "fig6a_application_ranked_results"),
        (images[1], "fig6b_application_pathway_audit"),
    ]
    for path, name in outputs:
        screenshot = plt.imread(path)
        height, width = screenshot.shape[:2]
        display_width = 7.35
        display_height = display_width * height / width
        fig, ax = plt.subplots(figsize=(display_width, display_height))
        ax.imshow(screenshot)
        ax.axis("off")
        fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
        save(fig, out_dir, name, tight=False)


# --------------------------------------------------------------------------
# Figure 2 -- term size within the corrected ranking
# --------------------------------------------------------------------------
def fig_specificity(reports: Dict[str, dict], out_dir: Path) -> None:
    """Describe term size within the final-PPS ranking."""
    report = reports.get("hf_inflammatory") or next(iter(reports.values()))
    rows = sorted(
        report["ranked_hypotheses"],
        key=lambda row: float(row.get("nes_score") or 0.0),
        reverse=True,
    )[:15]
    missing_term_size = [
        row.get("pathway_name", row.get("pathway_id", "unknown"))
        for row in rows
        if not isinstance(row.get("term_size"), (int, float))
        or row.get("term_size") <= 0
    ]
    if missing_term_size:
        print(
            "  ! top-PPS rows lack annotated term_size; skipping fig2: "
            + ", ".join(missing_term_size)
        )
        return

    sizes = [r["term_size"] for r in rows]
    scores = [float(r.get("nes_score") or 0.0) for r in rows]
    ranks = list(range(1, len(rows) + 1))
    rho = spearman([float(v) for v in sizes], [float(v) for v in scores])

    fig, ax = plt.subplots(figsize=(6.6, 3.45))
    ax.scatter(
        sizes,
        scores,
        color=BLUE,
        marker="o",
        s=36,
        edgecolors=SURFACE,
        linewidths=0.9,
        zorder=3,
    )
    label_offsets = [(7, 8), (7, -11), (-10, 8), (-10, -11)]
    for size, score, rank in zip(sizes, scores, ranks):
        offset = label_offsets[(rank - 1) % len(label_offsets)]
        ax.annotate(
            str(rank),
            (size, score),
            xytext=offset,
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=6.3,
            color=INK,
            weight="normal",
            bbox={"boxstyle": "round,pad=0.12", "facecolor": SURFACE,
                  "edgecolor": "none", "alpha": 0.88},
        )

    ax.set_xlabel("Annotated term size (genes)")
    ax.set_ylabel("Final Pathway Prioritization Score")
    ax.margins(x=0.08, y=0.18)
    despine(ax)

    annotation = f"Spearman rho = {rho:+.2f}; n = {len(rows)}" if rho is not None else f"n = {len(rows)}"
    annotation += f"\nrange = {min(sizes):,}-{max(sizes):,} genes; labels show rank"
    ax.text(
        0.98,
        0.94,
        annotation,
        transform=ax.transAxes,
        fontsize=7,
        color=INK_2,
        ha="right",
        va="top",
    )
    ax.text(
        0.0,
        -0.25,
        "Heart-failure benchmark. Specificity enters PPS, so this is a consistency check.",
        transform=ax.transAxes,
        fontsize=7,
        color=MUTED,
    )
    save(fig, out_dir, "fig2_term_specificity")


# --------------------------------------------------------------------------
# Figure 3 -- literature saturation is discriminative
# --------------------------------------------------------------------------
def fig_saturation(reports: Dict[str, dict], out_dir: Path) -> None:
    """Exact-query PubMed counts, with redundant tier encodings.

    The capped abstract display set is shown separately so it cannot be mistaken
    for the full count returned by the exact PubMed query.
    """
    report = reports.get("hf_inflammatory") or next(iter(reports.values()))
    rows = [r for r in report["ranked_hypotheses"]
            if (r.get("score_components") or {}).get("query_tier") == "strict"
            and (r.get("score_components") or {}).get("novelty_confidence")
                in {"verified", "verified_gap"}
            and isinstance((r.get("score_components") or {}).get("pubmed_hit_count"), int)
            and r["score_components"]["pubmed_hit_count"] >= 0][:20]
    if not rows:
        print("  ! no hit counts available, skipping fig3")
        return

    hits = [max(r["score_components"]["pubmed_hit_count"], 0) for r in rows]
    tiers = [r["score_components"].get("novelty_tier", "Established") for r in rows]
    retrieved = [r.get("citation_count", 0) for r in rows]
    ranks = list(range(1, len(rows) + 1))

    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    bars = ax.bar(
        ranks,
        hits,
        bottom=1,
        color=[TIER_COLOR.get(t, MUTED) for t in tiers],
        edgecolor=INK_2,
        linewidth=0.35,
        width=0.62,
        zorder=3,
    )
    for bar, tier_name in zip(bars, tiers):
        bar.set_hatch(TIER_HATCH.get(tier_name, ""))
    for x, hit, tier_name in zip(ranks, hits, tiers):
        if hit == 0:
            ax.scatter(
                x,
                1,
                marker=TIER_MARKER.get(tier_name, "o"),
                s=25,
                facecolor=TIER_COLOR.get(tier_name, MUTED),
                edgecolor=INK_2,
                linewidth=0.45,
                zorder=4,
            )
    ax.plot(
        ranks,
        [c + 1 for c in retrieved],
        color=VERMILLION,
        linewidth=1.6,
        marker="D",
        markersize=3.7,
        markerfacecolor=SURFACE,
        markeredgewidth=0.9,
        zorder=4,
        label="abstract display set (capped)",
    )

    for x, y in zip(ranks, hits):
        # The capped-retrieval line crosses this label band, so outline the text
        # rather than let the rank-1 count read through the marker.
        ax.text(x, y + 1.6, f"{y:,}", ha="center", va="bottom", fontsize=6.2,
                color=INK_2, rotation=90, zorder=6).set_path_effects(
                    [pe.withStroke(linewidth=1.8, foreground=SURFACE)])

    ax.set_yscale("log")
    ax.set_xlabel("Strict-query hypotheses ordered by Discovery Score")
    ax.set_ylabel("Three-clause PubMed records (count + 1)")
    ax.set_xticks(ranks)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))
    # Rotated value labels stand above the tallest bars; the log axis needs
    # headroom or the longest of them is clipped.
    ax.set_ylim(top=max(hits) * 3.2 if hits else None)
    despine(ax)

    handles = [
        plt.Rectangle(
            (0, 0), 1, 1,
            facecolor=TIER_COLOR[t],
            edgecolor=INK_2,
            linewidth=0.35,
            hatch=TIER_HATCH[t],
        )
        for t in TIER_ORDER if t in set(tiers)
    ]
    labels = [t for t in TIER_ORDER if t in set(tiers)]
    line = plt.Line2D(
        [], [], color=VERMILLION, linewidth=1.6, marker="D", markersize=3.7,
        markerfacecolor=SURFACE,
    )
    # Legend below the plot: inside the axes it overlapped the title and the
    # tall bars at both ends.
    ax.legend(handles + [line], labels + ["abstract display set (capped)"],
              ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    save(fig, out_dir, "fig3_literature_saturation")


# --------------------------------------------------------------------------
# Figure 4 -- temporal holdout
# --------------------------------------------------------------------------
def fig_holdout(holdout: dict, out_dir: Path) -> None:
    """Temporal holdout with conservative wording and distributional detail."""
    records = holdout.get("records") or []
    summary = holdout.get("summary") or {}
    if len(records) < 5:
        print("  ! too few holdout records, skipping fig4")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.15, 3.55),
                                   gridspec_kw={"width_ratios": [1.25, 1]})

    # Panel A -- the prespecified primary metric against normalized growth.
    xs = [r["discovery_pre"] for r in records]
    ys = [r["growth"] for r in records]
    present_tiers = [t for t in TIER_ORDER if any(r["tier_pre"] == t for r in records)]
    for tier_name in present_tiers:
        tier_records = [r for r in records if r["tier_pre"] == tier_name]
        ax1.scatter(
            [r["discovery_pre"] for r in tier_records],
            [r["growth"] for r in tier_records],
            color=TIER_COLOR[tier_name],
            marker=TIER_MARKER[tier_name],
            s=27,
            zorder=3,
            edgecolors=INK,
            linewidths=0.35,
            label=tier_name,
        )
    ax1.set_xlabel(f"{summary.get('cutoff', 'Cutoff')} Discovery Score")
    ax1.set_ylabel("Post-cutoff growth = new / (prior + 1)")
    ax1.set_title("A  Discovery Score versus subsequent growth", pad=39, loc="left")
    rho_growth = summary.get("spearman_discovery_vs_growth")
    rho_measurable = summary.get("spearman_discovery_vs_growth_measurable")
    n_measurable = summary.get("n_measurable")
    lines = []
    if rho_growth is not None:
        lines.append(f"\u03c1(Discovery, growth) = {rho_growth:+.4f}")
    if rho_measurable is not None and n_measurable is not None:
        lines.append(f"\u03c1 measurable-only = {rho_measurable:+.4f} (n={n_measurable})")
    if lines:
        lines.append(f"n = {len(records)} total")
        ax1.text(0.03, 0.06, chr(10).join(lines),
                 transform=ax1.transAxes, fontsize=7, color=INK, va="bottom",
                 zorder=5,
                 bbox={"boxstyle": "round,pad=0.28", "facecolor": SURFACE,
                       "edgecolor": GRID, "linewidth": 0.6, "alpha": 0.92})
    ax1.legend(
        loc="lower left",
        bbox_to_anchor=(0.0, 1.01),
        ncol=3,
        fontsize=6.5,
        handletextpad=0.4,
        columnspacing=0.8,
        frameon=True,
        facecolor=SURFACE,
        edgecolor=GRID,
        framealpha=1.0,
    )
    despine(ax1)

    # Panel B -- display the full distribution rather than mean-only bars.
    tiers = [t for t in TIER_ORDER if any(r["tier_pre"] == t for r in records)]
    values = [[r["growth"] for r in records if r["tier_pre"] == t] for t in tiers]
    means = [statistics.mean(group) for group in values]
    by_tier = summary.get("growth_by_tier") or {}
    medians = [
        (by_tier.get(tier_name) or {}).get("median_growth", statistics.median(group))
        for tier_name, group in zip(tiers, values)
    ]
    ypos = list(range(len(tiers)))[::-1]
    box = ax2.boxplot(
        values,
        positions=ypos,
        vert=False,
        widths=0.56,
        patch_artist=True,
        showfliers=True,
        boxprops={"linewidth": 0.65, "edgecolor": INK_2},
        whiskerprops={"linewidth": 0.65, "color": INK_2},
        capprops={"linewidth": 0.65, "color": INK_2},
        medianprops={"linewidth": 1.1, "color": INK},
        flierprops={"marker": ".", "markersize": 2.5, "markeredgecolor": INK_2},
    )
    for patch, tier_name in zip(box["boxes"], tiers):
        patch.set_facecolor(TIER_COLOR[tier_name])
        patch.set_alpha(0.32)
        patch.set_hatch(TIER_HATCH[tier_name])
    label_x = max(max(group) for group in values) * 1.10
    for y, mean_value, median_value, group in zip(ypos, means, medians, values):
        ax2.scatter(mean_value, y, marker="D", s=22, color=INK, zorder=4)
        ax2.text(
            label_x,
            y,
            f"median {median_value:.4f}; n={len(group)}",
            va="center",
            fontsize=6.7,
            color=INK_2,
        )
    ax2.set_yticks(ypos)
    ax2.set_yticklabels(tiers, fontsize=7.5)
    ax2.set_xlabel("Post-cutoff growth = new / (prior + 1)")
    ax2.set_title("B  Growth distributions by cutoff tier")
    ax2.set_xlim(left=0, right=max(max(group) for group in values) * 1.42)
    ax2.text(0.98, 0.03, "diamond: mean; center line: median",
             transform=ax2.transAxes, ha="right", va="bottom",
             fontsize=6.4, color=MUTED)
    ax2.grid(axis="y", visible=False)
    despine(ax2)

    fig.tight_layout()
    save(fig, out_dir, "fig4_temporal_holdout")


# --------------------------------------------------------------------------
# Figure 5 -- negative controls
# --------------------------------------------------------------------------
def fig_controls(reports: Dict[str, dict], manifest: dict, out_dir: Path) -> None:
    """Real seed panels vs random and off-target gene sets.

    Counts are split into interpretable, Unverified, and Ungrounded evidence
    states. The separation is the result: every negative-control hypothesis
    falls in the Ungrounded class, while lexical or measurement failures cannot
    be mistaken for interpretable novelty calls in the cardiovascular panels.
    """
    display_names = {
        "arrhythmia_channels": "Inherited arrhythmia",
        "mi_ischemic": "Myocardial infarction",
        "dcm_structural": "Dilated cardiomyopathy",
        "hf_inflammatory": "Heart failure",
        "olfactory": "Olfactory-receptor control",
        "random_1": "Random control 1",
        "random_2": "Random control 2",
    }
    rows = []
    for name, meta in manifest.items():
        report = reports.get(name)
        hyps = report["ranked_hypotheses"] if report else []
        confidences = [
            str((h.get("score_components") or {}).get("novelty_confidence") or "")
            for h in hyps
        ]
        tiers = [
            str((h.get("score_components") or {}).get("novelty_tier") or "")
            for h in hyps
        ]
        interpretable = sum(
            confidence in {"verified", "verified_gap"}
            for confidence in confidences
        )
        ungrounded = sum(
            confidence == "ungrounded_seeds" or tier == "Ungrounded"
            for confidence, tier in zip(confidences, tiers)
        )
        unverified = len(hyps) - interpretable - ungrounded
        rows.append({
            "name": display_names.get(name, name.replace("_", " ").title()),
            "kind": meta.get("kind", "real"),
            "interpretable": interpretable,
            "unverified": unverified,
            "ungrounded": ungrounded,
        })
    if not rows:
        return

    rows.sort(key=lambda r: (r["kind"] != "real", -r["interpretable"]))
    fig, ax = plt.subplots(figsize=(7.0, 0.42 * len(rows) + 1.85))
    ypos = list(range(len(rows)))[::-1]

    interpretable_bars = ax.barh(
        ypos,
        [r["interpretable"] for r in rows],
        color=BLUE,
        edgecolor=INK_2,
        linewidth=0.35,
        hatch="////",
        height=0.6,
        zorder=3,
        label="Interpretable strict-query evidence",
    )
    unverified_bars = ax.barh(
        ypos,
        [r["unverified"] for r in rows],
        left=[r["interpretable"] for r in rows],
        color=PURPLE,
        edgecolor=INK_2,
        linewidth=0.35,
        hatch="oo",
        height=0.6,
        zorder=3,
        label="Unverified prerequisite or query",
    )
    ungrounded_bars = ax.barh(
        ypos,
        [r["ungrounded"] for r in rows],
        left=[r["interpretable"] + r["unverified"] for r in rows],
        color=VERMILLION,
        edgecolor=INK_2,
        linewidth=0.35,
        hatch="++++",
        height=0.6,
        zorder=3,
        label="Ungrounded: insufficient seed-disease literature",
    )
    for y, r in zip(ypos, rows):
        total = r["interpretable"] + r["unverified"] + r["ungrounded"]
        ax.text(
            total,
            y,
            f"  I/U/G {r['interpretable']}/{r['unverified']}/{r['ungrounded']} "
            f"(n={total})",
            va="center",
            fontsize=6.8,
            color=INK_2,
        )

    real_total = sum(
        r["interpretable"] + r["unverified"] + r["ungrounded"]
        for r in rows if r["kind"] == "real"
    )
    real_ungrounded = sum(r["ungrounded"] for r in rows if r["kind"] == "real")
    control_total = sum(
        r["interpretable"] + r["unverified"] + r["ungrounded"]
        for r in rows if r["kind"] != "real"
    )
    control_ungrounded = sum(r["ungrounded"] for r in rows if r["kind"] != "real")
    # The grounding invariant now lives in the caption, so echo it at build time
    # to keep the manuscript's stated counts checkable against the figure data.
    print(f"  grounding invariant: {control_ungrounded}/{control_total} controls "
          f"and {real_ungrounded}/{real_total} cardiovascular hypotheses Ungrounded")

    real_count = sum(1 for r in rows if r["kind"] == "real")
    if 0 < real_count < len(rows):
        divider_y = (ypos[real_count - 1] + ypos[real_count]) / 2
        ax.axhline(divider_y, color=GRID, linewidth=1.0, zorder=1)

    ax.set_yticks(ypos)
    ax.set_yticklabels([r["name"] for r in rows], fontsize=7.5)
    ax.set_xlabel("Pathway hypotheses reported")
    ax.margins(x=0.28)
    ax.grid(axis="y", visible=False)
    despine(ax)
    ax.legend(
        handles=[interpretable_bars, unverified_bars, ungrounded_bars],
        ncol=3,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.01),
        frameon=True,
        facecolor=SURFACE,
        edgecolor=GRID,
        framealpha=1.0,
    )
    save(fig, out_dir, "fig5_negative_controls")


# --------------------------------------------------------------------------
# Figure 7 -- representative cardiovascular exact-query gaps
# --------------------------------------------------------------------------
def fig_discovery_gaps(
    reports: Dict[str, dict], manifest: dict, out_dir: Path
) -> None:
    """Quantify every verified exact-query gap in the regenerated real panels."""
    disease_label = {
        "dcm_structural": "Dilated cardiomyopathy",
        "arrhythmia_channels": "Inherited arrhythmia",
        "mi_ischemic": "Myocardial infarction",
        "hf_inflammatory": "Heart failure",
    }
    display_name = {
        "Signaling by NTRK2 (TRKB)": "NTRK2 (TRKB) signaling",
        "cGMP-PKG signaling pathway": "cGMP-PKG signaling",
        "Oxytocin signaling pathway": "Oxytocin signaling",
        "ADP signalling through P2Y purinoceptor 12": "P2Y12 signaling",
    }
    panel_color = {
        "dcm_structural": BLUE,
        "arrhythmia_channels": GREEN,
        "mi_ischemic": ORANGE,
        "hf_inflammatory": SKY,
    }
    panel_marker = {
        "dcm_structural": "o",
        "arrhythmia_channels": "s",
        "mi_ischemic": "^",
        "hf_inflammatory": "D",
    }

    rows = []
    for run_name, report in reports.items():
        if (manifest.get(run_name) or {}).get("kind") != "real":
            continue
        for match in report.get("ranked_hypotheses", []):
            score = match.get("score_components") or {}
            hits = score.get("pubmed_hit_count")
            if hits != 0 or score.get("novelty_confidence") != "verified_gap":
                continue
            fold = match.get("fold_enrichment")
            if fold is None:
                print(
                    f"  ! verified gap lacks fold enrichment: {run_name} / "
                    f"{match.get('pathway_name', '')}"
                )
                continue
            empirical_q = score.get("empirical_qvalue")
            exact_name = match.get("pathway_name", "")
            rows.append({
                "run": run_name,
                "rank": int(match.get("rank") or 0),
                "pathway": display_name.get(exact_name, exact_name),
                "disease": disease_label.get(run_name, run_name.replace("_", " ").title()),
                "fold": float(fold),
                "q": float(empirical_q) if isinstance(empirical_q, (int, float)) else None,
                "hits": hits,
                "discovery": score.get("discovery_score"),
            })

    if not rows:
        print("  ! no complete discovery-gap candidates, skipping fig7")
        return
    panel_order = {"dcm_structural": 0, "arrhythmia_channels": 1,
                   "mi_ischemic": 2, "hf_inflammatory": 3}
    rows.sort(key=lambda row: (panel_order.get(row["run"], 99), row["rank"]))

    folds = [row["fold"] for row in rows]
    ypos = list(range(len(rows)))[::-1]
    fig, ax = plt.subplots(figsize=(7.15, max(3.3, 0.52 * len(rows) + 1.4)))

    for y, row in zip(ypos, rows):
        color = panel_color[row["run"]]
        marker = panel_marker[row["run"]]
        ax.hlines(y, 1.0, row["fold"], color=color, linewidth=1.6, zorder=2)
        ax.scatter(
            row["fold"],
            y,
            s=52,
            marker=marker,
            color=color,
            edgecolors=INK,
            linewidths=0.45,
            zorder=3,
        )
        discovery = row["discovery"]
        discovery_text = f"  D={discovery:.3f}" if isinstance(discovery, (int, float)) else ""
        q_text = f"{row['q']:.5f}" if row["q"] is not None else "not testable"
        # Every row in this figure has zero exact-query records by construction,
        # so that clause belongs in the caption, not repeated on eight rows.
        ax.text(
            row["fold"] + 0.28,
            y,
            f"{row['fold']:.1f}×  q={q_text}{discovery_text}",
            va="center",
            fontsize=6.8,
            color=INK_2,
        )

    ax.axvline(1.0, color=GRID, linewidth=0.9, linestyle="--", zorder=1)
    ax.set_yticks(ypos)
    ax.set_yticklabels(
        [f"{row['pathway']}\n{row['disease']}" for row in rows],
        fontsize=7.2,
    )
    ax.set_xlabel("Fold enrichment (observed / expected overlap)")
    # No in-axes title or footnote: IEEE runs the description in the caption, and
    # duplicating it here cost horizontal room the row labels needed.
    ax.set_xlim(0.8, max(folds) * 1.62)
    ax.grid(axis="y", visible=False)
    despine(ax)
    save(fig, out_dir, "fig7_cardiovascular_discovery_gaps")


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------
def table_top_hypotheses(reports: Dict[str, dict], out_dir: Path) -> None:
    """Table 2: top discoveries per seed panel, as CSV and markdown."""
    header = ["seed_panel", "rank", "pathway", "source", "discovery_score",
              "novelty_tier", "pps", "enrichment_p_adj", "fold_enrichment",
              "perm_q", "genes", "pubmed_hits"]
    rows: List[List[str]] = []

    for name, report in sorted(reports.items()):
        for h in report["ranked_hypotheses"][:5]:
            sc = h.get("score_components") or {}
            q = sc.get("empirical_qvalue")
            fold = h.get("fold_enrichment")
            hits = sc.get("pubmed_hit_count")
            rows.append([
                name,
                str(h.get("rank", "")),
                h.get("pathway_name", ""),
                h.get("source_db", ""),
                f"{sc['discovery_score']:.3f}" if sc.get("discovery_score") is not None else "",
                sc.get("novelty_tier", ""),
                f"{h.get('nes_score', 0):.3f}",
                f"{h.get('p_adj', 1):.2e}",
                f"{fold:.1f}" if fold else "",
                f"{q:.3g}" if q is not None else "n/t",
                str(h.get("evidence_count", "")),
                str(hits) if isinstance(hits, int) and hits >= 0 else "",
            ])

    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "table2_top_hypotheses.csv"
    csv_path.write_text(
        "\n".join(",".join('"' + c.replace('"', '""') + '"' for c in r)
                  for r in [header] + rows),
        encoding="utf-8")
    md = ["| " + " | ".join(header) + " |",
          "|" + "|".join("---" for _ in header) + "|"]
    md += ["| " + " | ".join(r) + " |" for r in rows]
    (out_dir / "table2_top_hypotheses.md").write_text("\n".join(md), encoding="utf-8")
    print(f"  wrote table2_top_hypotheses.csv / .md ({len(rows)} rows)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="bench/out/manifest.json")
    ap.add_argument("--holdout", default="bench/out/holdout.json")
    ap.add_argument("--out", default="paper")
    args = ap.parse_args()

    style()
    out_root = Path(args.out)
    fig_dir, tbl_dir = out_root / "figures", out_root / "tables"

    fig_workflow(fig_dir)
    fig_interface(fig_dir)

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    reports: Dict[str, dict] = {}
    for name, meta in manifest.items():
        run_json = Path(meta["json"])
        if run_json.exists():
            report = load_report(run_json)
            if report and report.get("ranked_hypotheses"):
                reports[name] = report
    print(f"loaded {len(reports)} reports with hypotheses")

    if reports:
        fig_specificity(reports, fig_dir)
        fig_saturation(reports, fig_dir)
        fig_controls(reports, manifest, fig_dir)
        fig_discovery_gaps(reports, manifest, fig_dir)
        table_top_hypotheses(reports, tbl_dir)

    holdout_path = Path(args.holdout)
    if holdout_path.exists():
        fig_holdout(json.loads(holdout_path.read_text(encoding="utf-8")), fig_dir)
    else:
        print("  ! no holdout results yet, skipping fig4")


if __name__ == "__main__":
    main()
