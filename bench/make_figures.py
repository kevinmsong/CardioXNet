"""Generate the manuscript figures and tables from benchmark outputs.

Figures are built for print: a single light surface, no dark mode, direct value
labels on every mark (the palette's low-contrast slots require that relief), and
vector PDF alongside a 300 dpi PNG.

Usage:
    python bench/make_figures.py --manifest bench/out/manifest.json \
        --holdout bench/out/holdout.json --out paper
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Validated categorical palette (light surface #fcfcfb).
# node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a,#eda100" --mode light
#   -> all hard gates PASS; contrast WARN on slots 3-4 is discharged by the
#      direct value labels every figure carries.
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
SURFACE = "#ffffff"
GRID = "#e4e3de"

TIER_ORDER = ["Highly Novel", "Novel", "Emerging", "Established"]
TIER_COLOR = {
    "Highly Novel": BLUE,
    "Novel": AQUA,
    "Emerging": YELLOW,
    "Established": MUTED,
}


def style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.titleweight": "bold",
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
    })


def despine(ax, keep=("left", "bottom")) -> None:
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in keep)


def save(fig, out_dir: Path, name: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {name}.pdf / .png")


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
# Figure 2 -- ranking behaviour before vs after the scoring correction
# --------------------------------------------------------------------------
def fig_specificity(reports: Dict[str, dict], out_dir: Path) -> None:
    """Gene-set size of the top-ranked terms: the generic-term bias, quantified.

    The legacy score multiplied significance by raw gene count, so the ranking
    reduced to "sort by set size". Plotting term size against rank shows the
    corrected score no longer does that.
    """
    report = reports.get("hf_inflammatory") or next(iter(reports.values()))
    rows = report["ranked_hypotheses"][:15]

    sizes = [r.get("term_size") or r.get("evidence_count") or 0 for r in rows]
    names = [r["pathway_name"] for r in rows]
    ranks = list(range(1, len(rows) + 1))

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    ax.bar(ranks, sizes, color=BLUE, width=0.62, zorder=3)
    for x, y in zip(ranks, sizes):
        ax.text(x, y, f"{y:,}", ha="center", va="bottom", fontsize=6.5, color=INK_2)

    ax.set_xlabel("Discovery Score rank")
    ax.set_ylabel("Annotated term size (genes)")
    ax.set_title("Top-ranked terms are specific, not merely large")
    ax.set_xticks(ranks)
    ax.margins(y=0.16)
    despine(ax)

    caption = "top hit: " + (names[0][:52] + "…" if len(names[0]) > 52 else names[0])
    ax.text(0.0, -0.30, caption, transform=ax.transAxes, fontsize=7, color=MUTED)
    save(fig, out_dir, "fig2_term_specificity")


# --------------------------------------------------------------------------
# Figure 3 -- literature saturation is discriminative
# --------------------------------------------------------------------------
def fig_saturation(reports: Dict[str, dict], out_dir: Path) -> None:
    """PubMed corpus size per pathway, log scale, coloured by novelty tier.

    The point of the panel: the counts span orders of magnitude. The earlier
    implementation counted retrieved abstracts, which the retrieval cap pinned
    near a constant, leaving novelty with no signal to read.
    """
    report = reports.get("hf_inflammatory") or next(iter(reports.values()))
    rows = [r for r in report["ranked_hypotheses"]
            if isinstance((r.get("score_components") or {}).get("pubmed_hit_count"), int)
            and r["score_components"]["pubmed_hit_count"] >= 0][:20]
    if not rows:
        print("  ! no hit counts available, skipping fig3")
        return

    hits = [max(r["score_components"]["pubmed_hit_count"], 0) for r in rows]
    tiers = [r["score_components"].get("novelty_tier", "Established") for r in rows]
    retrieved = [r.get("citation_count", 0) for r in rows]
    ranks = list(range(1, len(rows) + 1))

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    ax.bar(ranks, [h + 1 for h in hits],
           color=[TIER_COLOR.get(t, MUTED) for t in tiers], width=0.62, zorder=3)
    ax.plot(ranks, [c + 1 for c in retrieved], color=ORANGE, linewidth=2,
            marker="o", markersize=3.5, zorder=4,
            label="abstracts retrieved (capped)")

    for x, y in zip(ranks, hits):
        ax.text(x, y + 1, f"{y:,}", ha="center", va="bottom", fontsize=6.2,
                color=INK_2, rotation=90)

    ax.set_yscale("log")
    ax.set_xlabel("Discovery Score rank")
    ax.set_ylabel("PubMed records + 1")
    ax.set_title("Literature saturation spans three orders of magnitude")
    ax.set_xticks(ranks)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))
    despine(ax)

    handles = [plt.Rectangle((0, 0), 1, 1, color=TIER_COLOR[t])
               for t in TIER_ORDER if t in set(tiers)]
    labels = [t for t in TIER_ORDER if t in set(tiers)]
    line = plt.Line2D([], [], color=ORANGE, linewidth=2, marker="o", markersize=3.5)
    ax.legend(handles + [line], labels + ["abstracts retrieved (capped)"],
              ncol=3, loc="upper left", bbox_to_anchor=(0, 1.0))
    save(fig, out_dir, "fig3_literature_saturation")


# --------------------------------------------------------------------------
# Figure 4 -- temporal holdout
# --------------------------------------------------------------------------
def fig_holdout(holdout: dict, out_dir: Path) -> None:
    """Does novelty at the cutoff predict subsequent publication growth?"""
    records = holdout.get("records") or []
    summary = holdout.get("summary") or {}
    if len(records) < 5:
        print("  ! too few holdout records, skipping fig4")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.9, 3.2),
                                   gridspec_kw={"width_ratios": [1.25, 1]})

    # Panel A: novelty at cutoff vs subsequent growth
    xs = [r["novelty_pre"] for r in records]
    ys = [r["growth"] for r in records]
    cols = [TIER_COLOR.get(r["tier_pre"], MUTED) for r in records]
    ax1.scatter(xs, ys, c=cols, s=26, zorder=3, edgecolors=SURFACE, linewidths=0.6)
    ax1.set_xlabel(f"Literature novelty at {summary.get('cutoff', 'cutoff')}")
    ax1.set_ylabel("Post-cutoff growth\n(records after / records before)")
    ax1.set_title("A  Novelty predicts later publication")
    rho = summary.get("spearman_novelty_vs_growth")
    if rho is not None:
        ax1.text(0.03, 0.94, f"Spearman ρ = {rho:+.2f}  (n = {len(records)})",
                 transform=ax1.transAxes, fontsize=7.5, color=INK, va="top")
    despine(ax1)

    # Panel B: growth by tier assigned at the cutoff
    by_tier = summary.get("growth_by_tier") or {}
    tiers = [t for t in TIER_ORDER if t in by_tier]
    means = [by_tier[t]["mean_growth"] for t in tiers]
    ns = [by_tier[t]["n"] for t in tiers]
    ypos = list(range(len(tiers)))[::-1]
    ax2.barh(ypos, means, color=[TIER_COLOR[t] for t in tiers], height=0.6, zorder=3)
    for y, m, n in zip(ypos, means, ns):
        ax2.text(m, y, f"  {m:.2f}  (n={n})", va="center", fontsize=7, color=INK_2)
    ax2.set_yticks(ypos)
    ax2.set_yticklabels(tiers, fontsize=7.5)
    ax2.set_xlabel("Mean post-cutoff growth")
    ax2.set_title("B  Growth by tier at cutoff")
    ax2.margins(x=0.30)
    ax2.grid(axis="y", visible=False)
    despine(ax2)

    fig.tight_layout()
    save(fig, out_dir, "fig4_temporal_holdout")


# --------------------------------------------------------------------------
# Figure 5 -- negative controls
# --------------------------------------------------------------------------
def fig_controls(reports: Dict[str, dict], manifest: dict, out_dir: Path) -> None:
    """Real seed panels vs random and off-target gene sets."""
    names, counts, kinds = [], [], []
    for name, meta in manifest.items():
        report = reports.get(name)
        n = len(report["ranked_hypotheses"]) if report else 0
        names.append(name.replace("_", " "))
        counts.append(n)
        kinds.append(meta.get("kind", "real"))
    if not names:
        return

    order = sorted(range(len(names)), key=lambda i: (kinds[i] != "real", -counts[i]))
    names = [names[i] for i in order]
    counts = [counts[i] for i in order]
    kinds = [kinds[i] for i in order]

    fig, ax = plt.subplots(figsize=(6.6, 0.42 * len(names) + 1.5))
    ypos = list(range(len(names)))[::-1]
    colors = [BLUE if k == "real" else ORANGE for k in kinds]
    ax.barh(ypos, counts, color=colors, height=0.6, zorder=3)
    for y, c in zip(ypos, counts):
        ax.text(c, y, f"  {c}", va="center", fontsize=7.5, color=INK_2)

    ax.set_yticks(ypos)
    ax.set_yticklabels(names, fontsize=7.5)
    ax.set_xlabel("Cardiac pathway hypotheses reported")
    ax.set_title("Negative controls yield few or no hypotheses")
    ax.margins(x=0.18)
    ax.grid(axis="y", visible=False)
    despine(ax)

    handles = [plt.Rectangle((0, 0), 1, 1, color=BLUE),
               plt.Rectangle((0, 0), 1, 1, color=ORANGE)]
    ax.legend(handles, ["cardiovascular seed panel", "negative control"],
              ncol=2, loc="lower right")
    save(fig, out_dir, "fig5_negative_controls")


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
        table_top_hypotheses(reports, tbl_dir)

    holdout_path = Path(args.holdout)
    if holdout_path.exists():
        fig_holdout(json.loads(holdout_path.read_text(encoding="utf-8")), fig_dir)
    else:
        print("  ! no holdout results yet, skipping fig4")


if __name__ == "__main__":
    main()
