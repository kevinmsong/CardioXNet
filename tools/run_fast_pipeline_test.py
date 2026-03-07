import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.pipeline import Pipeline


GENES = ["MYH7", "MYBPC3", "TTN", "LMNA", "SCN5A"]
CONFIG_OVERRIDES = {
    "disease_context": "cardiomyopathy",
    "string_neighbor_count": 15,
    "top_hypotheses_count": 5,
    "semantic_max_hypotheses_for_literature": 3,
    "pubmed_max_results": 10,
    "permutation_test_enabled": False,
    "output_formats": ["json"],
}


async def run():
    pipeline = Pipeline(config_overrides=CONFIG_OVERRIDES)
    print("Analysis ID:", pipeline.analysis_id)

    try:
        result = await pipeline.run(GENES)
        out = ROOT / "outputs" / f"{pipeline.analysis_id}_smoke.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        print("Pipeline completed, results written to", out)
    except Exception as e:
        import traceback

        print("Pipeline failed:", e)
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run())
