import asyncio
import sys
from pathlib import Path

# Ensure repo on path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

async def main():
    try:
        from app.main import lifespan, app
        print('Imported app and lifespan')

        # Run startup portion of lifespan manually
        ctx = lifespan(app)
        try:
            await ctx.__aenter__()
            print('Lifespan startup completed - app should be ready')
            # Keep alive for 20 seconds to observe any errors
            await asyncio.sleep(20)
            print('Completed wait — exiting normally')
        finally:
            await ctx.__aexit__(None, None, None)
            print('Lifespan shutdown complete')
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    asyncio.run(main())
