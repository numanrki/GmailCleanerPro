# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all Google packages
google_auth_datas, google_auth_binaries, google_auth_hiddenimports = collect_all('google.auth')
google_oauth_datas, google_oauth_binaries, google_oauth_hiddenimports = collect_all('google_auth_oauthlib')
googleapiclient_datas, googleapiclient_binaries, googleapiclient_hiddenimports = collect_all('googleapiclient')

all_datas = google_auth_datas + google_oauth_datas + googleapiclient_datas
all_binaries = google_auth_binaries + google_oauth_binaries + googleapiclient_binaries
all_hiddenimports = google_auth_hiddenimports + google_oauth_hiddenimports + googleapiclient_hiddenimports

a = Analysis(
    ['gmail_cleaner_pro.py'],
    pathex=[],
    binaries=all_binaries,
    datas=[('app_icon.ico', '.')] + all_datas,
    hiddenimports=all_hiddenimports + [
        'unittest',
        'unittest.mock',
        'httplib2',
        'uritemplate',
        'cachetools',
        'pyasn1',
        'pyasn1_modules',
        'rsa',
        'requests',
        'certifi',
        'charset_normalizer',
        'idna',
        'urllib3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pandas', 'numpy', 'scipy', 'matplotlib',
        'PIL', 'cv2', 'sklearn', 'tensorflow', 'torch',
        'IPython', 'notebook', 'jupyter',
    ],
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
    name='GmailCleanerPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python*.dll'],
    runtime_tmpdir=None,
    console=False,  # Hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)
