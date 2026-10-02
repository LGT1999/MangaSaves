"""Comprueba el arranque del paquete Windows en una base temporal."""

from contextlib import closing
import argparse
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from time import monotonic, sleep


def stop_process(process):
    """Cierra únicamente el proceso de prueba y sus hijos de PyInstaller."""
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        import _winapi

        # Tool Help funciona sin WMI ni los permisos adicionales de taskkill /T.
        # https://learn.microsoft.com/windows/win32/api/tlhelp32/ns-tlhelp32-processentry32w
        class ProcessEntry(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260),
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
        kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        for name in ("Process32FirstW", "Process32NextW"):
            function = getattr(kernel, name)
            function.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
            function.restype = wintypes.BOOL
        snapshot = kernel.CreateToolhelp32Snapshot(2, 0)  # TH32CS_SNAPPROCESS
        if snapshot == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        parents = {}
        try:
            entry = ProcessEntry()
            entry.dwSize = ctypes.sizeof(entry)
            found = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
            while found:
                parents[entry.th32ProcessID] = entry.th32ParentProcessID
                found = kernel.Process32NextW(snapshot, ctypes.byref(entry))
        finally:
            _winapi.CloseHandle(snapshot)
        descendants = []
        pending = [process.pid]
        while pending:
            parent = pending.pop()
            children = [pid for pid, parent_id in parents.items() if parent_id == parent]
            descendants.extend(children)
            pending.extend(children)
        for pid in reversed(descendants):
            try:
                handle = _winapi.OpenProcess(0x100001, False, pid)  # SYNCHRONIZE | PROCESS_TERMINATE
            except OSError as exc:
                if exc.winerror == 87:  # El hijo ya terminó.
                    continue
                raise
            try:
                _winapi.TerminateProcess(handle, 0)
                if _winapi.WaitForSingleObject(handle, 10000) != 0:
                    raise RuntimeError("El proceso hijo de verificación no se cerró.")
            finally:
                _winapi.CloseHandle(handle)
        if descendants:
            # El padre de --onefile retira sus archivos extraídos al salir el hijo.
            process.wait(timeout=10)
    if process.poll() is None:
        process.terminate()
    process.wait(timeout=10)


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=root / "MangaSaves" / "dist" / "MangaSaves" / "MangaSaves.exe")
    executable = parser.parse_args().exe.resolve()
    if not executable.is_file():
        raise SystemExit("Compila primero con tools/build_app.py.")
    with tempfile.TemporaryDirectory() as temp:
        env = {
            **os.environ, "QT_QPA_PLATFORM": "offscreen",
            "TEMP": temp, "TMP": temp, "TMPDIR": temp,
        }
        path = Path(temp) / "smoke.db"
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        process = subprocess.Popen(
            [str(executable), "--db", str(path)], cwd=temp, env=env, creationflags=flags
        )
        try:
            ready = False
            deadline = monotonic() + 15
            while monotonic() < deadline and process.poll() is None:
                if path.is_file():
                    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
                        has_index = conn.execute(
                            "SELECT 1 FROM sqlite_master WHERE name='idx_lecturas_fecha_v2'"
                        ).fetchone() is not None
                        columns = {row[1] for row in conn.execute("PRAGMA table_info(lecturas)")}
                        ready = has_index and "valoracion" in columns
                    if ready:
                        break
                sleep(0.1)
            if not ready:
                raise RuntimeError(f"El ejecutable no inicializó la base. Código: {process.poll()}")
            sleep(1)
            if process.poll() is not None:
                raise RuntimeError(f"El ejecutable se cerró durante el arranque: {process.returncode}")
        finally:
            stop_process(process)
    print("OK: ejecutable inicia y crea la base temporal con sus índices y valoración.")


if __name__ == "__main__":
    main()
