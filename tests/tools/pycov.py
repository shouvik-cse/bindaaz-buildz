"""Tiny line-coverage meter for the scraper modules (no extra packages needed).
Usage: python tests/tools/pycov.py   → runs tests/py with pytest and prints coverage per file.
(In CI you can use pytest-cov instead: pytest --cov=scraper tests/py)"""
import sys
import threading
from pathlib import Path

import os
import pytest

os.environ["BB_PYCOV"] = "1"
ROOT = Path(__file__).resolve().parents[2]
TARGETS = {str(p): set() for p in (ROOT / "scraper").glob("*.py")}


BY_NAME = {Path(f).name: f for f in TARGETS}


def tracer(frame, event, arg):
    f = frame.f_code.co_filename
    p = Path(f)
    if p.parent.name == "scraper" and p.name in BY_NAME:      # the repo's file, or a test copy of it
        TARGETS[BY_NAME[p.name]].add(frame.f_lineno)
        return tracer
    return None


def executable_lines(path):
    code = compile(Path(path).read_text(encoding="utf-8"), path, "exec")
    lines, stack = set(), [code]
    while stack:
        c = stack.pop()
        lines.update(l for _, _, l in c.co_lines() if l)
        stack.extend(k for k in c.co_consts if hasattr(k, "co_lines"))
    return lines


sys.settrace(tracer)
threading.settrace(tracer)
rc = pytest.main(["-q", "-p", "no:cacheprovider", str(ROOT / "tests" / "py")])
sys.settrace(None)
tot_hit = tot_all = 0
print("\nLine coverage of scraper/*.py:")
for f, hit in sorted(TARGETS.items()):
    ex = executable_lines(f)
    h = len(ex & hit)
    tot_hit += h; tot_all += len(ex)
    print(f"  {Path(f).name:16} {h:4}/{len(ex):<4} {100 * h / len(ex):5.1f}%")
print(f"  {'TOTAL':16} {tot_hit:4}/{tot_all:<4} {100 * tot_hit / tot_all:5.1f}%")
sys.exit(rc)
