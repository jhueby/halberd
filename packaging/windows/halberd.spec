# PyInstaller spec for Halberd BAS Windows executable
# Build: pip install pyinstaller && pyinstaller packaging/windows/halberd.spec

import os
import sys
from pathlib import Path

block_cipher = None
ROOT = Path(os.path.abspath(os.path.join(SPECPATH, '..', '..')))

a = Analysis(
    [str(ROOT / 'halberd' / 'cli.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'halberd' / 'library' / 'atomic'), 'halberd/library/atomic'),
        (str(ROOT / 'halberd' / 'library' / 'chains'), 'halberd/library/chains'),
        (str(ROOT / 'halberd' / 'server' / 'templates'), 'halberd/server/templates'),
        (str(ROOT / 'halberd' / 'server' / 'static'), 'halberd/server/static'),
    ],
    hiddenimports=[
        'halberd',
        'halberd.cli',
        'halberd.agent',
        'halberd.agent.runner',
        'halberd.agent.client',
        'halberd.agent.sandbox',
        'halberd.agent.platform_info',
        'halberd.library',
        'halberd.library.loader',
        'halberd.library.importer',
        'halberd.library.atomic_schema',
        'halberd.library.chain_schema',
        'halberd.server',
        'halberd.server.app',
        'halberd.server.database',
        'halberd.server.models',
        'halberd.server.schemas',
        'halberd.server.routes',
        'halberd.server.routes.agents',
        'halberd.server.routes.library',
        'halberd.server.routes.campaigns',
        'halberd.server.routes.results',
        'halberd.report',
        'halberd.report.generator',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='halberd',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
