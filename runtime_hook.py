import os
import sys

# Add the PyInstaller temp folder to PATH so python3*.dll is found
meipass = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
if meipass and meipass not in os.environ.get('PATH', ''):
    os.environ['PATH'] = meipass + os.pathsep + os.environ.get('PATH', '')
