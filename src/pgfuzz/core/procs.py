"""Process hygiene: no worker may outlive the run that started it.

Two mechanisms, both Linux-specific and no-ops elsewhere:

* :func:`die_with_parent` asks the kernel to SIGKILL the calling process when its
  parent dies (``prctl(PR_SET_PDEATHSIG)``). Pool workers and engine workers call it
  first thing, so killing the run (even with SIGKILL) takes every worker down.
* :func:`lead_process_group` makes the run the leader of a new process group and turns
  SIGINT/SIGTERM into "terminate the whole group, then exit", so Ctrl-C or ``kill``
  of the run stops engine workers that a pool worker started as well.
"""

from __future__ import annotations

import ctypes
import os
import signal
import sys
from typing import Any

_PR_SET_PDEATHSIG = 1


def die_with_parent(sig: int = signal.SIGKILL) -> bool:
    """Kill this process with ``sig`` when its parent exits. Returns True if armed."""
    if not sys.platform.startswith("linux"):
        return False
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(_PR_SET_PDEATHSIG, int(sig), 0, 0, 0) != 0:
            return False
    except (OSError, AttributeError):
        return False
    # the parent may already be gone (race between fork and prctl)
    if os.getppid() == 1:
        os._exit(1)
    return True


_handlers_installed = False


def lead_process_group() -> int:
    """Become a process-group leader and kill the group on SIGINT/SIGTERM.

    Returns the group id. Safe to call more than once."""
    global _handlers_installed
    if not hasattr(os, "setpgid"):
        return 0
    try:
        if os.getpgid(0) != os.getpid():
            os.setpgid(0, 0)
    except OSError:
        pass
    pgid = os.getpgid(0)
    if not _handlers_installed:
        def _stop(signum: int, _frame: Any) -> None:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            try:
                os.killpg(pgid, signal.SIGTERM)
            except OSError:
                pass
            raise SystemExit(128 + signum)

        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)
        _handlers_installed = True
    return pgid


def group_members(pgid: int) -> list[int]:
    """PIDs in process group ``pgid`` other than the caller (Linux /proc scan)."""
    out = []
    me = os.getpid()
    for d in os.listdir("/proc"):
        if not d.isdigit() or int(d) == me:
            continue
        try:
            with open(f"/proc/{d}/stat", encoding="utf-8") as f:
                fields = f.read().rsplit(")", 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != "Z":
                out.append(int(d))
        except (OSError, IndexError, ValueError):
            continue
    return out
