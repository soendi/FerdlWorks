import winreg
import sys
from lib.logger import get_logger

REG_PATH = r"SOFTWARE\SondereggerSoftware\FerdlWorks"


def _get_root():
    # Try HKLM first (where installer writes), then fall back to HKCU
    return winreg.HKEY_LOCAL_MACHINE


def _open_key_for_read(path):
    """Try to open key from HKLM first, then HKCU."""
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            return winreg.OpenKey(root, path, 0, winreg.KEY_READ)
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f"Key not found in HKLM or HKCU: {path}")


def reg_write(key_name, value, is_registry_root=False):
    try:
        if is_registry_root:
            path = REG_PATH
        else:
            path = f"{REG_PATH}\\{key_name.rsplit('\\', 1)[0]}" if "\\" in key_name else REG_PATH
            key_name = key_name.rsplit("\\", 1)[-1] if "\\" in key_name else key_name
        handle = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, path)
        if isinstance(value, int):
            winreg.SetValueEx(handle, key_name, 0, winreg.REG_DWORD, value)
        else:
            winreg.SetValueEx(handle, key_name, 0, winreg.REG_SZ, str(value))
        winreg.CloseKey(handle)
        return True
    except Exception as ex:
        get_logger().error(f"Registry write error ({key_name}): {ex}")
        return False


def reg_read(key_name, default=None):
    try:
        path = f"{REG_PATH}\\{key_name.rsplit('\\', 1)[0]}" if "\\" in key_name else REG_PATH
        key_name = key_name.rsplit("\\", 1)[-1] if "\\" in key_name else key_name
        handle = _open_key_for_read(path)
        value, _ = winreg.QueryValueEx(handle, key_name)
        winreg.CloseKey(handle)
        return value
    except FileNotFoundError:
        return default
    except Exception as ex:
        get_logger().error(f"Registry read error ({key_name}): {ex}")
        return default


def reg_delete_key(key_name_full):
    try:
        sub_key = f"{REG_PATH}\\{key_name_full}" if key_name_full else REG_PATH
        winreg.DeleteKey(winreg.HKEY_LOCAL_MACHINE, sub_key)
        return True
    except FileNotFoundError:
        return True
    except Exception as ex:
        get_logger().error(f"Registry delete error ({sub_key}): {ex}")
        return False


def reg_delete_all():
    try:
        _delete_recursive(winreg.HKEY_LOCAL_MACHINE, REG_PATH)
        return True
    except Exception as ex:
        get_logger().error(f"Registry delete all error: {ex}")
        return False


def _delete_recursive(hkey, sub_key):
    try:
        handle = winreg.OpenKey(hkey, sub_key, 0, winreg.KEY_READ | winreg.KEY_WRITE)
        while True:
            try:
                child = winreg.EnumKey(handle, 0)
                _delete_recursive(handle, f"{sub_key}\\{child}")
            except OSError:
                break
        winreg.CloseKey(handle)
        winreg.DeleteKey(hkey, sub_key)
    except FileNotFoundError:
        pass
