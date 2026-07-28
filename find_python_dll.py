"""Find the Python 3 DLL path for PyInstaller bundling."""
import sysconfig, os, glob

dll_name = sysconfig.get_config_var('LDLIBRARY')

# 1. sys.base_prefix
if dll_name:
    p = os.path.join(sys.base_prefix, dll_name)
    if os.path.exists(p):
        print(p); exit()

# 2. sys.prefix
if dll_name:
    p = os.path.join(sys.prefix, dll_name)
    if os.path.exists(p):
        print(p); exit()

# 3. hostedtoolcache (GitHub Actions)
for ev in ('RUNNER_TOOL_CACHE', 'Python_ROOT_DIR', 'Python_ROOT'):
    root = os.environ.get(ev, '')
    if root:
        for f in glob.glob(os.path.join(root, '**', 'python3*.dll'), recursive=True):
            if os.path.exists(f):
                print(f); exit()

# 4. neben python.exe im PATH
for d in os.environ.get('PATH', '').split(os.pathsep):
    if 'python' in d.lower():
        for f in glob.glob(os.path.join(d, 'python3*.dll')):
            if os.path.exists(f):
                print(f); exit()

# 5. DLLs Ordner
dlls = os.path.join(os.path.dirname(os.__file__), 'DLLs')
for f in glob.glob(os.path.join(dlls, 'python3*.dll')):
    if os.path.exists(f):
        print(f); exit()

print('NOT_FOUND')
