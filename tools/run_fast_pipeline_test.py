import sys, json
sys.path.insert(0, '.')
from app.services.fast_pipeline import FastPipeline

pipeline = FastPipeline()
print('Analysis ID:', pipeline.analysis_id)

# Run pipeline synchronously in new event loop
import asyncio

genes = ['MYH7','MYBPC3','TTN','LMNA','SCN5A']

async def run():
    try:
        result = await pipeline.run(genes)
        out = 'outputs/analysis_test_MyGenes.json'
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        print('Pipeline completed, results written to', out)
    except Exception as e:
        import traceback
        print('Pipeline failed:', e)
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(run())
