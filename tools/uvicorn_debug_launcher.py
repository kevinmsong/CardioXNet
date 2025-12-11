import sys
import traceback
from pathlib import Path
import faulthandler
import uvicorn


def write_debug(msg: str):
    log_file = Path(__file__).resolve().parents[1] / 'server_log_debug.txt'
    try:
        with open(log_file, 'a', encoding='utf-8') as out:
            out.write(msg + '\n')
    except Exception:
        pass


if __name__ == '__main__':
    try:
        # Enable faulthandler to dump tracebacks on fatal signals
        faulthandler.enable()

        repo_root = Path(__file__).resolve().parents[1]
        # Ensure repo root is on sys.path so 'app' package can be imported
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))

        write_debug('Starting uvicorn programmatically (debug launcher)')
        write_debug(f'Working dir: {Path.cwd()}')
        write_debug(f'Repo root: {repo_root}')
        write_debug(f'sys.path[0:5]: {sys.path[0:5]}')

        # Run uvicorn programmatically - this blocks until shutdown
        uvicorn.run('app.main:app', host='127.0.0.1', port=8000, log_level='debug')
    except Exception:
        write_debug('Exception during uvicorn.run:')
        tb = traceback.format_exc()
        write_debug(tb)
        print('Exception during uvicorn.run; details written to server_log_debug.txt')
