#!/usr/bin/env python3
"""Prefix bisect replay driver.

Reads a saved shuffled file list and performs a binary-prefix search to
find the minimal predecessor file that, when placed before the culprit
nodeid in that ordering, reproduces the failing test from the saved
randomized run.

Writes per-run junit xml and logs to the specified output directory.
"""
import argparse
import os
import shlex
import subprocess
import sys
import sysconfig
import xml.etree.ElementTree as ET


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--shuffled", default="/tmp/shuffled_files.txt")
    p.add_argument(
        "--culprit",
        required=True,
        help="Culprit nodeid (file::testname or file path).",
    )
    p.add_argument("--out", default="/tmp/researcharr-bisect")
    return p.parse_args()


def nodeid_to_classname_and_name(nodeid: str):
    # nodeid like tests/foo/bar.py::test_name or tests/foo/bar.py::Class::test
    path, *rest = nodeid.split("::")
    mod = path.replace("/", ".").rstrip(".py")
    # name is last token
    name = rest[-1] if rest else ""
    return mod, name


def run_pytest(prefix_files, culprit_nodeid, out_dir, idx):
    xml_path = os.path.join(out_dir, f"replay_prefix_{idx}.xml")
    log_path = os.path.join(out_dir, f"replay_prefix_{idx}.log")

    # Prefer project's .venv python if available so installed deps are found
    venv_py = os.path.join(os.getcwd(), ".venv", "bin", "python")
    py_exec = venv_py if os.path.exists(venv_py) else sys.executable

    args = [
        py_exec,
        "-m",
        "pytest",
        "--override-ini=addopts=",
        "-p",
        "no:xdist",
        "--junit-xml",
        xml_path,
        "--maxfail=1",
        "--disable-warnings",
    ]
    # pass culprit last so the prefix order is preserved
    args.extend(prefix_files)
    args.append(culprit_nodeid)

    env = os.environ.copy()
    # Ensure triage envs
    env["RESEARCHARR_DISABLE_PLUGINS"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env.pop("PYTEST_ADDOPTS", None)

    # Prepend site-packages so subprocess has access to installed deps
    site_packages = sysconfig.get_paths()["purelib"]
    env["PYTHONPATH"] = site_packages + (":" + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")

    with open(log_path, "wb") as logf:
        proc = subprocess.run(args, stdout=logf, stderr=logf, env=env)

    return proc.returncode, xml_path, log_path


def xml_shows_culprit_failure(xml_path, culprit_nodeid):
    if not os.path.exists(xml_path):
        return False
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return False
    root = tree.getroot()
    mod, name = nodeid_to_classname_and_name(culprit_nodeid)
    # pytest uses classname like tests.module.submodule
    for testcase in root.findall(".//testcase"):
        tc_class = testcase.get("classname") or ""
        tc_name = testcase.get("name") or ""
        if tc_class == mod and tc_name == name:
            # test recorded here; check for failure child
            if testcase.find("failure") is not None or testcase.find("error") is not None:
                return True
            return False
    return False


def main():
    args = parse_args()
    out = args.out
    os.makedirs(out, exist_ok=True)

    with open(args.shuffled, "r") as f:
        files = [line.strip() for line in f.readlines() if line.strip()]

    # If culprit is a nodeid with path, prefer preserving that nodeid; but tests list contains file paths.
    culprit_nodeid = args.culprit

    n = len(files)
    left = 0
    right = n
    found_len = None

    while left < right:
        mid = (left + right) // 2
        prefix = files[: mid]
        idx = mid
        print(f"running prefix len {mid} -> xml={out}/replay_prefix_{idx}.xml", flush=True)
        rc, xml_path, log_path = run_pytest(prefix, culprit_nodeid, out, idx)
        print(f" rc={rc} -> {log_path}", flush=True)
        # If junit xml shows culprit failure, the minimal predecessor is in this prefix
        if xml_shows_culprit_failure(xml_path, culprit_nodeid):
            found_len = mid
            # search left half
            right = mid
        else:
            # move right
            left = mid + 1

    if found_len is None:
        print("No failing prefix found")
    else:
        pred = files[found_len - 1] if found_len > 0 else ""
        print(f"Found failing prefix length: {found_len}")
        print(f"Predecessor: {pred}")


if __name__ == "__main__":
    main()
