"""Run the CardioXNet benchmark suite: real seed sets plus negative controls.

Each analysis is a separate subprocess so that one failure cannot take down the
suite, and so per-run wall time is measured cleanly.

Seed sets
---------
Three cardiovascular seed panels with distinct biology (inflammatory, structural
cardiomyopathy, electrophysiology) plus two negative controls:

  * ``random_genes``  -- protein-coding genes drawn at random. A discovery tool
    must not return a confident cardiac story for these.
  * ``olfactory``     -- olfactory receptors: a coherent gene family with no
    cardiac role, which tests whether coherence alone is enough to produce
    cardiac hits.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.gene_background import protein_coding_background

SEED_SETS = {
    "hf_inflammatory": {
        "genes": ["VEGFA", "MMP9", "IL6", "TNF", "ACE"],
        "disease": "heart_failure",
        "kind": "real",
        "note": "Inflammatory/remodelling axis in heart failure.",
    },
    "dcm_structural": {
        "genes": ["MYH7", "TTN", "LMNA", "MYBPC3", "TNNT2"],
        "disease": "cardiomyopathy",
        "kind": "real",
        "note": "Sarcomeric and nuclear-envelope genes in dilated cardiomyopathy.",
    },
    "arrhythmia_channels": {
        "genes": ["SCN5A", "KCNQ1", "KCNH2", "RYR2", "CACNA1C"],
        "disease": "arrhythmia",
        "kind": "real",
        "note": "Cardiac ion channels underlying inherited arrhythmia syndromes.",
    },
    "mi_ischemic": {
        "genes": ["LDLR", "APOB", "PCSK9", "NOS3", "EDN1"],
        "disease": "myocardial_infarction",
        "kind": "real",
        "note": "Lipid handling and endothelial tone in ischaemic heart disease.",
    },
}

NEGATIVE_CONTROLS = {
    "olfactory": {
        "genes": ["OR51E2", "OR2W1", "OR1A1", "OR5K1", "OR10A4"],
        "disease": "heart_failure",
        "kind": "negative",
        "note": "Olfactory receptors: coherent family, no cardiac role.",
    },
}


def random_control(seed: int, n: int = 5) -> dict:
    rng = random.Random(seed)
    pool = protein_coding_background()
    return {
        "genes": rng.sample(pool, n),
        "disease": "heart_failure",
        "kind": "negative",
        "note": f"Random protein-coding genes (seed={seed}).",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="bench/out")
    ap.add_argument("--preset", default="balanced")
    ap.add_argument("--only", nargs="*", help="restrict to these run names")
    ap.add_argument("--n-random", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=2400)
    args = ap.parse_args()

    runs = dict(SEED_SETS)
    runs.update(NEGATIVE_CONTROLS)
    for i in range(args.n_random):
        runs[f"random_{i + 1}"] = random_control(seed=1000 + i)

    if args.only:
        runs = {k: v for k, v in runs.items() if k in args.only}

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}

    for name, spec in runs.items():
        out_json = out_dir / f"{name}.json"
        out_log = out_dir / f"{name}.log"
        print(f"\n=== {name} ({spec['kind']}) : {','.join(spec['genes'])} "
              f"[{spec['disease']}] ===", flush=True)

        cmd = [
            sys.executable, str(ROOT / "bench" / "run_pipeline.py"),
            "--genes", ",".join(spec["genes"]),
            "--disease", spec["disease"],
            "--out", str(out_json),
            "--preset", args.preset,
        ]
        t0 = time.time()
        with out_log.open("w", encoding="utf-8") as fh:
            proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT,
                                  timeout=args.timeout, cwd=ROOT)
        elapsed = time.time() - t0

        manifest[name] = {
            **spec,
            "returncode": proc.returncode,
            "elapsed_s": round(elapsed, 1),
            "json": str(out_json),
            "log": str(out_log),
            "ok": proc.returncode == 0 and out_json.exists(),
        }
        print(f"    -> rc={proc.returncode} in {elapsed:.0f}s", flush=True)

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"\nWROTE {manifest_path}")
    for name, m in manifest.items():
        print(f"  {'OK ' if m['ok'] else 'FAIL'} {name:<22} {m['elapsed_s']:>7.0f}s")


if __name__ == "__main__":
    main()
