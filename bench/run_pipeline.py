"""Run the CardioXNet pipeline once and dump the result. Used by the benchmark."""
import argparse, asyncio, json, logging, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.pipeline import Pipeline


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genes", required=True, help="comma-separated seed gene symbols")
    ap.add_argument("--disease", default="heart_failure")
    ap.add_argument("--out", required=True)
    ap.add_argument("--preset", default="balanced")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    from app.web.constants import build_config
    overrides = build_config(args.preset, {})
    overrides["disease_context"] = args.disease

    genes = [g.strip().upper() for g in args.genes.split(",") if g.strip()]
    t0 = time.time()
    pipe = Pipeline(config_overrides=overrides)
    results = await pipe.run(genes)
    elapsed = time.time() - t0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = results if isinstance(results, dict) else results.model_dump()
    payload["_bench"] = {"elapsed_s": elapsed, "seed_genes": genes,
                         "disease": args.disease, "preset": args.preset}
    out.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    print(f"\nWROTE {out}  ({elapsed:.1f}s)")


if __name__ == "__main__":
    asyncio.run(main())
