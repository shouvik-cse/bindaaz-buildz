"""Shared test setup: import paths, a crawled sample catalogue, and a built copy of the site."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "scraper"), str(ROOT / "tests" / "fixtures")]

import crawl  # noqa: E402
import shops as fixture_shops  # noqa: E402


@pytest.fixture(scope="session")
def shops_cfg():
    return json.loads((ROOT / "scraper" / "shops.json").read_text(encoding="utf-8"))["shops"]


@pytest.fixture(scope="session")
def sample_catalog(tmp_path_factory, shops_cfg):
    """Run the real crawler end to end against the sample shop pages (no internet)."""
    out = tmp_path_factory.mktemp("crawl") / "catalog.json"
    fake = fixture_shops.fake_get_factory(shops_cfg)
    old_get, old_out, old_argv = crawl.get, crawl.OUT, sys.argv
    crawl.get, crawl.OUT, sys.argv = fake, out, ["crawl.py"]
    try:
        assert crawl.main() == 0
    finally:
        crawl.get, crawl.OUT, sys.argv = old_get, old_out, old_argv
    data = json.loads(out.read_text(encoding="utf-8"))
    data["_calls"] = fake.calls
    data["_path"] = str(out)
    return data


def build_copy(tmp: Path, catalog: dict | None, base="https://bindaaz-buildz.smart-builder.workers.dev", drop_images=False):
    """Copy the project to tmp, add the catalogue, run scraper/build_site.py, return the dist folder."""
    proj = tmp / "proj"
    shutil.copytree(ROOT, proj, ignore=shutil.ignore_patterns("dist", "tests", ".git", "__pycache__", "*.zip"))
    if catalog is not None:
        c = {k: v for k, v in catalog.items() if not k.startswith("_")}
        if drop_images:
            c = {**c, "items": [{k: v for k, v in i.items() if k != "i"} for i in c["items"]]}
        (proj / "site" / "catalog.json").write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    else:
        (proj / "site" / "catalog.json").unlink(missing_ok=True)
    if os.environ.get("BB_PYCOV"):          # coverage run: build in-process so the lines can be counted
        import contextlib, io, runpy
        buf, old = io.StringIO(), os.environ.get("SITE_BASE_URL")
        os.environ["SITE_BASE_URL"] = base
        try:
            with contextlib.redirect_stdout(buf):
                runpy.run_path(str(proj / "scraper" / "build_site.py"), run_name="__main__")
        finally:
            os.environ.pop("SITE_BASE_URL") if old is None else os.environ.__setitem__("SITE_BASE_URL", old)
        return proj / "dist", buf.getvalue()
    env = {**os.environ, "SITE_BASE_URL": base}
    res = subprocess.run([sys.executable, "scraper/build_site.py"], cwd=proj, env=env, capture_output=True, text=True, timeout=300)
    assert res.returncode == 0, res.stderr[-2000:]
    return proj / "dist", res.stdout


@pytest.fixture(scope="session")
def built_site(tmp_path_factory, sample_catalog):
    dist, log = build_copy(tmp_path_factory.mktemp("site"), sample_catalog)
    return dist
