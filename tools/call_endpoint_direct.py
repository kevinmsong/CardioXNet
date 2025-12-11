import asyncio
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

async def main(analysis_id: str):
    try:
        from app.api import endpoints
        print('Calling endpoints.get_analysis_results directly for', analysis_id)
        res = await endpoints.get_analysis_results(analysis_id)
        print('Return type:', type(res))
        # If it's a pydantic model, print dict
        try:
            print(res.dict())
        except Exception:
            print(res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: call_endpoint_direct.py <analysis_id>')
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
