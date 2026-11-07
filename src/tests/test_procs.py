import os
import signal
import subprocess
import sys
import time

import pytest

from pgfuzz.core.procs import group_members

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")

_CHILD = r"""
import multiprocessing as mp, sys, time
from pgfuzz.core.procs import die_with_parent

def grandchild():
    die_with_parent()
    time.sleep(60)

if __name__ == "__main__":
    p = mp.get_context("spawn").Process(target=grandchild, daemon=True)
    p.start()
    print(p.pid, flush=True)
    time.sleep(60)
"""


def test_grandchild_dies_when_parent_is_killed(tmp_path):
    script = tmp_path / "child.py"
    script.write_text(_CHILD)
    env = dict(os.environ, PYTHONPATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parent = subprocess.Popen([sys.executable, str(script)], stdout=subprocess.PIPE, text=True, env=env)
    gpid = int(parent.stdout.readline())
    parent.kill()   # SIGKILL: no handlers run, only PDEATHSIG can clean up
    parent.wait()
    for _ in range(50):
        try:
            os.kill(gpid, 0)
        except ProcessLookupError:
            return
        with open(f"/proc/{gpid}/stat") as f:
            if f.read().rsplit(")", 1)[1].split()[0] == "Z":
                return
        time.sleep(0.1)
    os.kill(gpid, signal.SIGKILL)
    pytest.fail("grandchild survived its parent")


def test_group_members_excludes_self():
    assert os.getpid() not in group_members(os.getpgid(0))
