"""Keep scheduled result snapshots and first-publication logs off the code branch.

Only narrowly selected data paths are read/written. Git's normal fast-forward
push protects concurrent changes; no force push or modification of main.
"""

from pathlib import Path
import argparse
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "codex/data-snapshots"
REF = "refs/remotes/origin/" + BRANCH


def git(*args, **kwargs):
    return subprocess.check_output(["git", *args], cwd=ROOT, **kwargs)


def allowed(name):
    return (
        name.startswith("data/open/results/")
        and name.endswith(".json")
        or (name.startswith("data/open/workbench/forecast_log_") and name.endswith(".json"))
    )


def restore():
    if not git("ls-remote", "--heads", "origin", BRANCH).strip():
        print("No snapshot branch yet; using bundled data.")
        return
    git("fetch", "origin", BRANCH + ":" + REF)
    for name in git("ls-tree", "-r", "--name-only", REF).decode().splitlines():
        if not allowed(name):
            raise RuntimeError("Unexpected path in data branch: " + name)
        payload = git("show", REF + ":" + name)
        obj = json.loads(payload)
        if not isinstance(obj, dict):
            raise ValueError("Snapshot must be an object")
        if "forecast_log_" in name:
            if obj.get("source_id") != "openfootball" or obj.get("license") != "CC0-1.0":
                raise ValueError("Refusing legacy forecast log")
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    print("Restored data revision " + git("rev-parse", REF).decode().strip())


def save():
    names = [str(p.relative_to(ROOT)) for p in (ROOT / "data/open/results").glob("*.json")] + [
        str(p.relative_to(ROOT)) for p in (ROOT / "data/open/workbench").glob("forecast_log_*.json")
    ]
    if not names:
        raise RuntimeError("No snapshots to save")
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        git("read-tree", "--empty", env=env)
        git("add", "-f", "--", *names, env=env)
        tree = git("write-tree", env=env).decode().strip()
    old = subprocess.run(
        ["git", "rev-parse", "--verify", REF], cwd=ROOT, capture_output=True, text=True
    )
    parent = old.stdout.strip() if old.returncode == 0 else None
    if parent and git("rev-parse", parent + "^{tree}").decode().strip() == tree:
        commit = parent
    else:
        commit = (
            git(
                "commit-tree",
                tree,
                *(["-p", parent] if parent else []),
                input=b"Refresh permitted result snapshots and prospective forecast record\n",
            )
            .decode()
            .strip()
        )
        git("push", "origin", commit + ":refs/heads/" + BRANCH)
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"], "a") as out:
            out.write("FOOTLYZER_DATA_REVISION=" + commit + "\n")
    print("Saved data revision " + commit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["restore", "save"])
    args = parser.parse_args()
    {"restore": restore, "save": save}[args.operation]()
