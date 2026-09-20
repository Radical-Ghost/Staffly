# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\staffly\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src\\staffly\\reports\\templates\\assets\\Endee.jpeg', 'staffly\\reports\\templates\\assets'),
        ('src\\staffly\\reports\\templates\\assets\\HNL.jpeg', 'staffly\\reports\\templates\\assets'),
        ('src\\staffly\\ui\\resources\\styles\\catppuccin_mocha.qss', 'staffly\\ui\\resources\\styles'),
        ('src\\staffly\\ui\\resources\\styles\\catppuccin_latte.qss', 'staffly\\ui\\resources\\styles'),
        ('src\\staffly\\ui\\resources\\icons\\chevron-down.svg', 'staffly\\ui\\resources\\icons'),
        ('src\\staffly\\ui\\resources\\icons\\chevron-down-dark.svg', 'staffly\\ui\\resources\\icons'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Staffly',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
