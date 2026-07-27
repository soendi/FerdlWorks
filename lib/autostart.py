import os
import sys
import subprocess
from lib.logger import get_logger
from lib.registry import reg_write, reg_read
from version import APP_NAME


def _get_exe_path():
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")


def needs_elevated_autostart():
    return False


def autostart_enable():
    logger = get_logger()
    exe_path = _get_exe_path()
    if needs_elevated_autostart():
        return _enable_task_scheduler(exe_path)
    else:
        return _enable_registry(exe_path)


def autostart_disable():
    logger = get_logger()
    if needs_elevated_autostart():
        return _disable_task_scheduler()
    else:
        return _disable_registry()


def autostart_is_enabled():
    if needs_elevated_autostart():
        return _task_exists()
    else:
        return bool(reg_read("AutoStartPath"))


def _enable_registry(exe_path):
    logger = get_logger()
    try:
        reg_write("AutoStartPath", exe_path)
        import winreg
        handle = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                                0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(handle, APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(handle)
        logger.info(f"Autostart (Registry) aktiviert: {exe_path}")
        return True
    except Exception as ex:
        logger.error(f"Autostart Registry fehlgeschlagen: {ex}")
        return False


def _disable_registry():
    logger = get_logger()
    try:
        reg_write("AutoStartPath", "")
        import winreg
        handle = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                                0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(handle, APP_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(handle)
        logger.info("Autostart (Registry) deaktiviert")
        return True
    except Exception as ex:
        logger.error(f"Autostart Registry deaktivieren fehlgeschlagen: {ex}")
        return False


def _enable_task_scheduler(exe_path):
    logger = get_logger()
    try:
        task_name = f"{APP_NAME} Autostart"
        xml = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>{APP_NAME} Autostart</Description></RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT10S</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{exe_path}</Command>
      <WorkingDirectory>{os.path.dirname(exe_path)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>'''
        temp_xml = os.path.join(os.environ["TEMP"], f"{APP_NAME}_autostart.xml")
        with open(temp_xml, "w", encoding="utf-16") as f:
            f.write(xml)
        subprocess.run(
            ["schtasks", "/Create", "/TN", task_name, "/XML", temp_xml, "/F"],
            check=True, capture_output=True, text=True)
        os.unlink(temp_xml)
        logger.info(f"Autostart (TaskSchedule) aktiviert: {task_name}")
        return True
    except Exception as ex:
        logger.error(f"TaskSchedule fehlgeschlagen: {ex}")
        return False


def _disable_task_scheduler():
    logger = get_logger()
    try:
        task_name = f"{APP_NAME} Autostart"
        subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"],
                       check=True, capture_output=True, text=True)
        logger.info(f"Autostart (TaskSchedule) deaktiviert: {task_name}")
        return True
    except Exception as ex:
        logger.error(f"TaskSchedule deaktivieren fehlgeschlagen: {ex}")
        return False


def _task_exists():
    task_name = f"{APP_NAME} Autostart"
    try:
        result = subprocess.run(["schtasks", "/Query", "/TN", task_name],
                                capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False
