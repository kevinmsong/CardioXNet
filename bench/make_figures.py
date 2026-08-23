"""Generate the manuscript figures and tables from benchmark outputs.

Figures are built for print: a single light surface, no dark mode, direct value
labels on every mark (the palette's low-contrast slots require that relief), and
vector PDF alongside a 600 dpi PNG.

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
TEAL, ACCENT_SOFT = "#0f766e", "#f0fdfa"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
SURFACE = "#ffffff"
GRID = "#e4e3de"

TIER_ORDER = ["Highly Novel", "Novel", "Emerging", "Established", "Ungrounded"]
TIER_COLOR = {
    "Highly Novel": BLUE,
    "Novel": AQUA,
    "Emerging": YELLOW,
    "Established": MUTED,
    # Not a weak result but an undefined one: the seed genes have too little
    # disease literature for any novelty call to mean anything.
    "Ungrounded": ORANGE,
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
        fig.savefig(out_dir / f"{name}.{ext}", dpi=600, bbox_inches="tight")
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
# Figure 1 -- complete analysis workflow
# --------------------------------------------------------------------------
def fig_workflow(out_dir: Path) -> None:
    """Compact overview of the evidence flow and auditable output."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    stages = [
        ("1", "Seed panel", "Validated genes\nand disease context"),
        ("2", "Network expansion", "STRING v12\npartners"),
        ("3", "Pathway evidence", "Multi-source\nenrichment"),
        ("4", "Secondary expansion", "Literature-linked\ngenes"),
        ("5", "Evidence ranking", "PPS, permutation,\nGTEx, druggability"),
        ("6", "Literature saturation", "Exact pathway x seed\nx disease corpus"),
    ]
    fig, ax = plt.subplots(figsize=(7.1, 3.15))
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 2)
    ax.axis("off")

    positions = [(0.03, 1.08), (1.03, 1.08), (2.03, 1.08),
                 (2.03, 0.20), (1.03, 0.20), (0.03, 0.20)]
    for index, ((number, title, detail), (x, y)) in enumerate(zip(stages, positions)):
        face = ACCENT_SOFT if index in (0, 5) else SURFACE
        edge = TEAL if index in (0, 5) else GRID
        box = FancyBboxPatch(
            (x, y), 0.84, 0.55,
            boxstyle="round,pad=0.025,rounding_size=0.045",
            linewidth=1.1, edgecolor=edge, facecolor=face,
        )
        ax.add_patch(box)
        ax.text(x + 0.08, y + 0.43, number, color=TEAL, fontsize=8,
                weight="bold", ha="left", va="center")
        ax.text(x + 0.20, y + 0.43, title, color=INK, fontsize=8,
                weight="bold", ha="left", va="center")
        ax.text(x + 0.08, y + 0.22, detail, color=INK_2, fontsize=7,
                ha="left", va="center", linespacing=1.25)

    arrows = [
        ((0.88, 1.355), (1.02, 1.355)),
        ((1.88, 1.355), (2.02, 1.355)),
        ((2.45, 1.07), (2.45, 0.78)),
        ((2.02, 0.475), (1.88, 0.475)),
        ((1.02, 0.475), (0.88, 0.475)),
    ]
    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>",
                                     mutation_scale=10, linewidth=1,
                                     color=MUTED))

    ax.text(0.03, 1.82,
            "CardioXNet converts a focused gene panel into auditable pathway hypotheses",
            color=INK, fontsize=10, weight="bold", ha="left")
    ax.text(0.03, 0.02,
            "Output: ranked hypotheses with gene lineage, enrichment effect size, empirical q-value, "
            "cardiac expression, druggability, and PubMed corpus size.",
            color=MUTED, fontsize=7, ha="left")
    save(fig, out_dir, "fig1_cardioxnet_workflow")


# --------------------------------------------------------------------------
# Figure 6 -- key application views
# --------------------------------------------------------------------------
def fig_interface(out_dir: Path) -> None:
    """Pair the ranked-results and pathway-audit views as a manuscript figure."""
    root = Path(__file__).resolve().parents[1]
    images = [
        root / "docs" / "screenshots" / "10-manuscript-ranked-results.png",
        root / "docs" / "screenshots" / "11-manuscript-pathway-evidence.png",
    ]
    if not all(path.exists() for path in images):
        print("  ! manuscript UI screenshots not found, skipping fig6")
        return

    fig, axes = plt.subplots(2, 1, figsize=(7.1, 8.6))
    labels = [
        "A  Ranked results summarize statistical, literature, and translational evidence",
        "B  A pathway audit exposes the exact literature gap and discovery lineage",
    ]
    for ax, path, label in zip(axes, images, labels):
        ax.imshow(plt.imread(path))
        ax.set_title(label, loc="left", pad=7, fontsize=8.5, weight="bold")
        ax.axis("off")
    fig.subplots_adjust(hspace=0.12)
    save(fig, out_dir, "fig6_application_evidence_views")


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

    fig, ax = plt.subplots(figsize=(6.8, 3.6))
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
    ax.set_title("Literature saturation spans three orders of magnitude", pad=14)
    ax.set_xticks(ranks)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))
    # Rotated value labels sit above the tallest bars, so the log axis needs
    # headroom or they collide with the title.
    ax.set_ylim(top=max(hits) * 12 if hits else None)
    despine(ax)

    handles = [plt.Rectangle((0, 0), 1, 1, color=TIER_COLOR[t])
               for t in TIER_ORDER if t in set(tiers)]
    labels = [t for t in TIER_ORDER if t in set(tiers)]
    line = plt.Line2D([], [], color=ORANGE, linewidth=2, marker="o", markersize=3.5)
    # Legend below the plot: inside the axes it overlapped the title and the
    # tall bars at both ends.
    ax.legend(handles + [line], labels + ["abstracts retrieved (capped)"],
              ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    save(fig, out_dir, "fig3_literature_saturation")


# --------------------------------------------------------------------------
# Figure 4 -- temporal holdout
# --------------------------------------------------------------------------
def fig_holdout(holdout: dict, out_dir: Path) -> None:
    """Temporal holdout: does novelty at the cutoff anticipate later publication?

    It does not, and the figure is drawn to show that rather than to obscure it.
    Panel A plots the raw relationship; panel B gives growth by the tier assigned
    at the cutoff. Reporting a null result plainly is the point of running the
    validation at all.
    """
    records = holdout.get("records") or []
    summary = holdout.get("summary") or {}
    if len(records) < 5:
        print("  ! too few holdout records, skipping fig4")
        return

    measurable = [r for r in records if r["hits_pre"] > 0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.9, 3.3),
                                   gridspec_kw={"width_ratios": [1.25, 1]})

    # Panel A -- novelty at cutoff vs subsequent publication volume.
    xs = [r["novelty_pre"] for r in records]
    ys = [r["hits_post"] + 1 for r in records]
    cols = [TIER_COLOR.get(r["tier_pre"], MUTED) for r in records]
    ax1.scatter(xs, ys, c=cols, s=24, zorder=3, edgecolors=SURFACE, linewidths=0.6)
    ax1.set_yscale("log")
    ax1.set_xlabel(f"Literature novelty at {summary.get('cutoff', 'cutoff')}")
    ax1.set_ylabel(f"Records published "
                   f"{int(summary.get('cutoff', 2020)) + 1}-{summary.get('through', '')} + 1")
    ax1.set_title("A  Novelty does not predict later work")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v):,}"))
    rho_abs = summary.get("spearman_novelty_vs_absolute")
    rho_growth = summary.get("spearman_novelty_vs_growth")
    lines = []
    if rho_abs is not None:
        lines.append(f"ρ(novelty, new records) = {rho_abs:+.2f}")
    if rho_growth is not None:
        lines.append(f"ρ(novelty, growth rate) = {rho_growth:+.2f}")
    if lines:
        lines.append(f"n = {len(records)}")
        ax1.text(0.03, 0.06, chr(10).join(lines),
                 transform=ax1.transAxes, fontsize=7, color=INK, va="bottom")
    despine(ax1)

    # Panel B -- growth by the tier assigned at the cutoff.
    by_tier = summary.get("growth_by_tier") or {}
    tiers = [t for t in TIER_ORDER if t in by_tier]
    means = [by_tier[t]["mean_growth"] for t in tiers]
    ns = [by_tier[t]["n"] for t in tiers]
    ypos = list(range(len(tiers)))[::-1]
    ax2.barh(ypos, means, color=[TIER_COLOR[t] for t in tiers], height=0.6, zorder=3)
    for y, m, n in zip(ypos, means, ns):
        ax2.text(m, y, f"  {m:.2f} (n={n})", va="center", fontsize=7, color=INK_2)
    ax2.set_yticks(ypos)
    ax2.set_yticklabels(tiers, fontsize=7.5)
    ax2.set_xlabel("Mean post-cutoff growth")
    ax2.set_title("B  Growth by tier at cutoff")
    ax2.margins(x=0.42)
    ax2.grid(axis="y", visible=False)
    despine(ax2)

    fig.tight_layout()
    save(fig, out_dir, "fig4_temporal_holdout")


# --------------------------------------------------------------------------
# Figure 5 -- negative controls
# --------------------------------------------------------------------------
def fig_controls(reports: Dict[str, dict], manifest: dict, out_dir: Path) -> None:
    """Real seed panels vs random and off-target gene sets.

    Counts are split into hypotheses carrying an interpretable novelty call and
    those flagged Ungrounded -- the seed genes have too little disease
    literature for novelty to mean anything. The separation is the result: every
    negative-control hypothesis falls in the Ungrounded class.
    """
    rows = []
    for name, meta in manifest.items():
        report = reports.get(name)
        hyps = report["ranked_hypotheses"] if report else []
        ungrounded = sum(
            1 for h in hyps
            if (h.get("score_components") or {}).get("novelty_tier") == "Ungrounded"
        )
        rows.append({
            "name": name.replace("_", " "),
            "kind": meta.get("kind", "real"),
            "grounded": len(hyps) - ungrounded,
            "ungrounded": ungrounded,
        })
    if not rows:
        return

    rows.sort(key=lambda r: (r["kind"] != "real", -r["grounded"]))
    fig, ax = plt.subplots(figsize=(6.6, 0.42 * len(rows) + 1.7))
    ypos = list(range(len(rows)))[::-1]

    ax.barh(ypos, [r["grounded"] for r in rows], color=BLUE, height=0.6, zorder=3,
            label="interpretable novelty call")
    ax.barh(ypos, [r["ungrounded"] for r in rows], left=[r["grounded"] for r in rows],
            color=ORANGE, height=0.6, zorder=3, label="Ungrounded (seeds lack disease literature)")
    for y, r in zip(ypos, rows):
        total = r["grounded"] + r["ungrounded"]
        ax.text(total, y, f"  {r['grounded']} / {total}", va="center",
                fontsize=7.5, color=INK_2)

    ax.set_yticks(ypos)
    ax.set_yticklabels([r["name"] for r in rows], fontsize=7.5)
    ax.set_xlabel("Pathway hypotheses reported")
    ax.set_title("Negative controls produce no interpretable novelty")
    ax.margins(x=0.20)
    ax.grid(axis="y", visible=False)
    despine(ax)
    ax.legend(ncol=1, loc="lower right")
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
        table_top_hypotheses(reports, tbl_dir)

    holdout_path = Path(args.holdout)
    if holdout_path.exists():
        fig_holdout(json.loads(holdout_path.read_text(encoding="utf-8")), fig_dir)
    else:
        print("  ! no holdout results yet, skipping fig4")


if __name__ == "__main__":
    main()
