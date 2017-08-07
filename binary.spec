# -*- mode: python -*-

block_cipher = None


a = Analysis(['dcos/cli/main.py'],
             datas=[('dcos/data/config-schema/*', 'dcos/data/config-schema'),
                    ('dcos/data/marathon/*', 'dcos/data/marathon'),
                    ('dcos/cli/data/help/*','dcos/cli/data/help'),
                    ('dcos/cli/data/schemas/*', 'dcos/cli/data/schemas')],
             binaries=None,
             hiddenimports=['_cffi_backend'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)


pyz = PYZ(a.pure,
          a.zipped_data,
          cipher=block_cipher)


exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='dcos',
          debug=False,
          strip=False,
          upx=True,
          console=True)
