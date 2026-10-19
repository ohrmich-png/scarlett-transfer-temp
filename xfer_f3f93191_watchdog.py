"""Scarlett Agent watchdog (runs on the desktop via pythonw, Startup folder).

Every 60s it checks:
  1. heartbeat.txt next to pc-agent.py is fresh (< 180s old)
  2. a python process running pc-agent.py exists
If either check fails, it kills leftover agent processes and relaunches
the agent the same way the Startup shortcut does (pythonw + tray mode).

Logs to watchdog.log next to this script. All prints are file-safe
(pythonw has no console).
"""
import os, sys, time, subprocess, datetime, ctypes
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_PY = os.path.join(HERE, "pc-agent.py")
HEARTBEAT = os.path.join(HERE, "heartbeat.txt")
LOG = os.path.join(HERE, "watchdog.log")

CHECK_EVERY = 60
HEARTBEAT_MAX_AGE = 180


def _hidden():
    """STARTUPINFO that keeps console windows from flashing (tray mode)."""
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si
    return None


_HIDDEN = _hidden()


def run_quiet(*args, **kwargs):
    kwargs.setdefault("startupinfo", _HIDDEN)
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("timeout", 30)
    if os.name == "nt":
        # CREATE_NO_WINDOW prevents the console window from being created
        # at all — STARTUPINFO alone still lets it flash briefly (seen live
        # on the laptop 2026-10-18: watchdog's 60s PowerShell scan flashing).
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
    return subprocess.run(*args, **kwargs)


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


def _iter_processes():
    """Yield (pid, exe_name, cmdline) using Toolhelp32 — pure ctypes, no child process.
    Replaces the old PowerShell Get-CimInstance scan, which flashed a visible
    console window every 60s despite STARTUPINFO/CREATE_NO_WINDOW (2026-10-18)."""
    if os.name != "nt":
        return
    kernel32 = ctypes.windll.kernel32
    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD),
                    ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_void_p),
                    ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD),
                    ("szExeFile", wintypes.CHAR * 260)]

    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        return
    try:
        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
        ok = kernel32.Process32First(snap, ctypes.byref(pe))
        while ok:
            pid = pe.th32ProcessID
            exe = pe.szExeFile.decode("utf-8", "replace")
            cmdline = _process_cmdline(kernel32, pid)
            yield pid, exe, cmdline
            ok = kernel32.Process32Next(snap, ctypes.byref(pe))
    finally:
        kernel32.CloseHandle(snap)


def _process_cmdline(kernel32, pid):
    """Read a process's command line via PEB — no child process spawned."""
    try:
        PROCESS_QUERY_LIMITED = 0x1000
        PROCESS_VM_READ = 0x0010
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED | PROCESS_VM_READ, False, pid)
        if not h:
            return ""
        try:
            # Use NtQueryInformationProcess via ntdll to get PEB address
            ntdll = ctypes.windll.ntdll
            class PROCESS_BASIC_INFORMATION(ctypes.Structure):
                _fields_ = [("Reserved1", ctypes.c_void_p),
                            ("PebBaseAddress", ctypes.c_void_p),
                            ("Reserved2", ctypes.c_void_p * 2),
                            ("UniqueProcessId", ctypes.c_void_p),
                            ("Reserved3", ctypes.c_void_p)]
            pbi = PROCESS_BASIC_INFORMATION()
            retlen = wintypes.ULONG()
            if ntdll.NtQueryInformationProcess(h, 0, ctypes.byref(pbi),
                                              ctypes.sizeof(pbi), ctypes.byref(retlen)) != 0:
                return ""
            peb = pbi.PebBaseAddress
            # PEB+0x20 -> RTL_USER_PROCESS_PARAMETERS; +0x70 -> CommandLine UNICODE_STRING
            ptr = ctypes.c_void_p()
            kernel32.ReadProcessMemory(h, peb + 0x20, ctypes.byref(ptr),
                                       ctypes.sizeof(ptr), None)
            if not ptr.value:
                return ""
            class UNICODE_STRING(ctypes.Structure):
                _fields_ = [("Length", wintypes.USHORT),
                            ("MaximumLength", wintypes.USHORT),
                            ("Buffer", wintypes.LPWSTR)]
            us = UNICODE_STRING()
            kernel32.ReadProcessMemory(h, ptr.value + 0x70, ctypes.byref(us),
                                       ctypes.sizeof(us), None)
            if not us.Buffer or us.Length == 0:
                return ""
            buf = ctypes.create_unicode_buffer(us.Length // 2 + 1)
            kernel32.ReadProcessMemory(h, us.Buffer, buf,
                                       us.Length, None)
            return buf.value
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        return ""


def _kill_pid(pid):
    """Terminate a process via TerminateProcess — no taskkill child process."""
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        h = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
        if h:
            kernel32.TerminateProcess(h, 1)
            kernel32.CloseHandle(h)
    except Exception as e:
        log(f"kill {pid} failed: {e}")


def agent_pids():
    """PIDs of processes running pc-agent.py (not this watchdog). Pure Python."""
    pids = []
    me = os.getpid()
    try:
        for pid, exe, cmdline in _iter_processes():
            if pid == me:
                continue
            if not exe.lower().startswith("python"):
                continue
            cl = (cmdline or "").lower()
            if "pc-agent.py" in cl and "watchdog.py" not in cl:
                pids.append(pid)
    except Exception as e:
        log(f"process scan failed: {e}")
    return pids


def heartbeat_age():
    try:
        return time.time() - os.path.getmtime(HEARTBEAT)
    except OSError:
        return None


def relaunch():
    # Relaunch via the Startup shortcut — this carries the right interpreter
    # (pythonw/pyw) and arguments on every machine, no hardcoded paths.
    lnk = os.path.join(os.environ.get("APPDATA", ""),
                       r"Microsoft\Windows\Start Menu\Programs\Startup",
                       "Scarlett Agent.lnk")
    if os.path.exists(lnk):
        log(f"relaunching agent via {lnk}")
        os.startfile(lnk)
        return
    # fallback: direct pythonw next to this interpreter
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    log(f"relaunching agent via {pyw} (fallback)")
    cf = subprocess.DETACHED_PROCESS
    if os.name == "nt":
        cf |= subprocess.CREATE_NO_WINDOW
    subprocess.Popen([pyw, AGENT_PY],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, startupinfo=_HIDDEN,
                     creationflags=cf)


def main():
    log("watchdog started")
    # grace period: let any in-flight bridge command finish before the
    # first health check (the old agent has no heartbeat yet, so the
    # first check would otherwise restart it mid-command)
    time.sleep(90)
    while True:
        try:
            pids = agent_pids()
            age = heartbeat_age()
            alive = bool(pids)
            fresh = age is not None and age < HEARTBEAT_MAX_AGE
            if alive and fresh:
                pass  # all good
            else:
                log(f"agent unhealthy (pids={pids}, heartbeat_age={age}) — restarting")
                for p in pids:
                    _kill_pid(p)
                time.sleep(3)
                # don't let a half-dead agent linger
                for p in agent_pids():
                    _kill_pid(p)
                relaunch()
        except Exception as e:
            log(f"watchdog error: {e}")
        time.sleep(CHECK_EVERY)


if __name__ == "__main__":
    main()
