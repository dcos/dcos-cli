# -*- mode: python -*-
import os
import os.path

block_cipher = None


a = Analysis(['../dcoscli/node/main.py'],
             pathex=['env/lib/python2.7/site-packages', os.getcwd(), os.path.dirname(os.getcwd())],
             binaries=None,
             datas=[('../dcoscli/data/help/node.txt', 'dcoscli/data/help')],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             win_no_prefer_redirects=None,
             win_private_assemblies=None,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='dcos-node',
          debug=False,
          strip=None,
          upx=True,
          console=True )
