r"""Run Pipeline directly (no API) with specified seed genes and save results.

Usage:
    .\venv\Scripts\python.exe tools\run_pipeline_direct.py
"""
from pathlib import Path
import sys

# Ensure repository root is on sys.path so `import app` works when run as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
import asyncio
import json
import os
import sys
import time

SEEDS = ["PIK3R1", "ITGB1", "SRC"]
OUT_DIR = "outputs"
CONFIG_OVERRIDES = {
    "disease_context": "diabetic_cardiomyopathy",
    "string_neighbor_count": 12,
    "top_hypotheses_count": 5,
    "semantic_max_hypotheses_for_literature": 3,
    "pubmed_max_results": 10,
    "permutation_test_enabled": False,
    "output_formats": ["json"],
}


def print_progress(stage: str, progress: float, message: str):
    print(f"[PROGRESS] {stage} - {progress:.1f}% - {message}", flush=True)


def main():
    try:
        # Create pipeline
        from app.services.pipeline import Pipeline

        pipeline = Pipeline(config_overrides=CONFIG_OVERRIDES)
        analysis_id = pipeline.analysis_id
        print(f"Created pipeline with id: {analysis_id}", flush=True)

        # Run pipeline
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def progress_cb(stage, prog, msg):
            print_progress(stage, prog, msg)
            # also give the pipeline a tiny sleep to allow logs to flush
            await asyncio.sleep(0.01)

        start = time.time()
        result = loop.run_until_complete(pipeline.run(SEEDS, progress_callback=progress_cb))
        loop.close()
        duration = time.time() - start

        # Save results
        os.makedirs(OUT_DIR, exist_ok=True)
        out_path = os.path.join(OUT_DIR, f"{analysis_id}_report_direct.json")
        with open(out_path, "w", encoding="utf8") as fh:
            json.dump(result, fh, indent=2, default=str)

        print(f"Pipeline completed in {duration:.1f}s. Results written to {out_path}", flush=True)
        return 0

    except Exception as e:
        import traceback
        print("Pipeline run failed:", e, flush=True)
        traceback.print_exc()
        return 2


if __name__ == '__main__':
    sys.exit(main())
