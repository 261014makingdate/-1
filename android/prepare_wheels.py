"""Prepare platform-independent Python wheels to embed in the APK."""
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
destination = root / 'wheelhouse'
destination.mkdir(exist_ok=True)
subprocess.run([
    sys.executable, '-m', 'pip', 'wheel', '--no-deps', '--no-cache-dir',
    '--no-binary=wrapt', '-r', str(root / 'requirements.txt'),
    '--wheel-dir', str(destination),
], env=dict(os.environ, WRAPT_INSTALL_EXTENSIONS='false'), check=True)
bad = [p.name for p in destination.glob('*.whl') if not p.name.endswith('none-any.whl')]
if bad:
    raise SystemExit(f'Non-portable wheels cannot be bundled: {bad}')
