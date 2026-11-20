"""Start the local workbench without embedding credentials or installing packages."""
import importlib.util
import os
from pathlib import Path
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HOST, PORT = '127.0.0.1', 8000
URL = f'http://{HOST}:{PORT}/'

def open_when_ready():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(100):
        try:
            with opener.open(URL + 'api/health', timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(URL)
                    return
        except OSError:
            pass
        time.sleep(0.2)

def main():
    missing = [name for name in ('uvicorn', 'fastapi', 'sqlalchemy', 'pydantic', 'multipart', 'yaml', 'requests', 'openpyxl') if importlib.util.find_spec(name) is None]
    if missing:
        print('Missing dependencies: ' + ', '.join(missing))
        print('Install with the SAME Python:')
        print(f'"{sys.executable}" -m pip install -r "{ROOT / "backend/requirements.txt"}"')
        return 1
    try:
        with socket.socket() as probe:
            probe.bind((HOST, PORT))
    except OSError:
        print(f'Port {PORT} is already in use. Check the running service; no process was stopped.')
        return 1
    sys.path.insert(0, str(ROOT / 'backend'))
    import uvicorn
    print(f'SPARK local workbench: {URL}', flush=True)
    print('Keep this window open. Press Ctrl+C to stop.', flush=True)
    print('Local demo data works without an API key. AI generation requires your own key.', flush=True)
    if os.environ.get('SPARK_NO_BROWSER') != '1':
        threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run('main:app', host=HOST, port=PORT, reload=False)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
