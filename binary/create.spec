# -*- mode: python -*-
import os
import subprocess


def _run_command(cmd):
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE)
    return process.communicate()[0].decode('utf-8').strip('\n ')

# find program's main function
main_file = _run_command(
    "git grep --no-color 'def main' | cut -d ':' -f 1")

# set __main__ to main() in 'main_file'
_run_command(
    "printf '\n\nif __name__ == \"__main__\":\n    main()' >> {}".format(
        main_file))

binary_name = _run_command("python -W ignore setup.py --name")
# get datafiles. Assuming under binary_name/data, alter if different
datas = []
main_dir = os.path.join(binary_name.replace('-', '_'), 'data')
for root, dirs, files in os.walk(main_dir):
    for f in files:
        path = os.path.join(root, f)
        datas += [(path, root)]

a = Analysis([main_file],
             pathex=[os.getcwd(),
                     'env/lib/python2.7/site-packages',
                     'cli/env/lib/python2.7/site-packages',
                     ],
             binaries=None,
             datas=datas,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=None)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name=binary_name,
          debug=False,
          strip=False,
          upx=True,
          console=True)
