#!/usr/bin/env python3
"""Prepare: python3 /mnt/sethDeploy.py --prepare
Deploy after restart: python3 /mnt/sethDeploy.py
"""
import argparse
import base64
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xmlrpc.client

URL = "http://localhost:8069"
DB = "RSN"
USER = "vanherck.s"
PASSWORD = "P@ssword01+"

REPOSITORY = "https://github.com/icefluffy/field-service.git"
BRANCH = os.environ.get("FSM_BRANCH", "")
ADDONS = Path("/mnt/extra-addons")
STATE = Path("/mnt/.fsmdeploy")
BASELINE = STATE / "successful.json"
PENDING = STATE / "pending.json"
PROJECT = Path("/mnt/field-service")


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def connect():
    password = "P@ssword01+" or getpass.getpass(f"Odoo password for {USER}: ")
    common = xmlrpc.client.ServerProxy(URL + "/xmlrpc/2/common")
    uid = common.authenticate(DB, USER, password, {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    proxy = xmlrpc.client.ServerProxy(URL + "/xmlrpc/2/object", allow_none=True)

    def call(model, method, *args, **kwargs):
        return proxy.execute_kw(DB, uid, password, model, method, list(args), kwargs)
    return call


def modules_in(root):
    return {p.name: p for p in root.iterdir()
            if p.is_dir() and (p / "__manifest__.py").is_file()}


def digest(folder):
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder)
        if any(x in {".git", "__pycache__", ".pytest_cache"} for x in rel.parts):
            continue
        if p.suffix in {".pyc", ".pyo"}:
            continue
        if p.is_symlink():
            raise RuntimeError(f"Symlink not supported in module: {p}")
        if p.is_file():
            h.update(str(rel).encode())
            h.update(b"\0")
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def installed(call):
    rows = call("ir.module.module", "search_read", [["state", "=", "installed"]], fields=["name"])
    return {r["name"]: r["id"] for r in rows}


def prepare():
    call = connect()
    live = installed(call)

    baseline = load(BASELINE, {"database": DB, "modules": {}})
    if baseline.get("database") != DB:
        raise RuntimeError(
            "Saved deployment state belongs to another database"
        )

    previous_pending = load(
        PENDING,
        {"database": DB, "modules": {}},
    )
    if previous_pending.get("database") != DB:
        raise RuntimeError(
            "Pending deployment belongs to another database"
        )

    unfinished = set(previous_pending.get("modules", {}))

    STATE.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="checkout-", dir=STATE) as temp:
        checkout = Path(temp) / "field-service"
        cmd = ["git", "clone", "--depth", "1"]
        if BRANCH:
            cmd += ["--branch", BRANCH]
        subprocess.run(cmd + [REPOSITORY, str(checkout)], check=True)
        commit = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        source = modules_in(checkout)
        if not source:
            raise RuntimeError("No module directories found at the repository root")
        removed = sorted((set(baseline["modules"]) & set(live)) - set(source))
        if removed:
            raise RuntimeError("Previously deployed installed modules disappeared from GitHub; review manually: " + ", ".join(removed))
        missing_unfinished = sorted(
            (unfinished & set(live)) - set(source)
        )
        if missing_unfinished:
            raise RuntimeError(
                "Unfinished installed modules disappeared from GitHub: "
                + ", ".join(missing_unfinished)
            )

        wanted = {}

        for name in sorted(source):
            if name not in live:
                print(f"SKIP uninstalled: {name}")
                continue

            fingerprint = digest(source[name])

            if (
                baseline["modules"].get(name) == fingerprint
                and name not in unfinished
            ):
                print(f"SKIP unchanged: {name}")
                continue

            reason = "RETRY" if name in unfinished else "CHANGED"
            print(f"{reason}: {name}")
            wanted[name] = fingerprint
            
        # Refresh the full repository, including root-level files.
        if PROJECT.is_symlink():
            raise RuntimeError(
                f"Refusing to replace a symlink: {PROJECT}"
            )

        if PROJECT.exists():
            shutil.rmtree(PROJECT)

        shutil.copytree(checkout, PROJECT)
        print(f"Full GitHub repository copied to {PROJECT}")

        if not wanted:
            print("No changed installed modules. No restart or upgrade needed.")
            return 0
        backup = Path(
            tempfile.mkdtemp(
                prefix=f"backup-{commit[:12]}-",
                dir=STATE,
            )
        )
        originals = []
        try:
            for name in sorted(wanted):
                destination = ADDONS / name
                if destination.is_symlink():
                    raise RuntimeError(f"Refusing to replace symlink: {destination}")
                if destination.exists():
                    old = backup / name
                    if old.exists():
                        raise RuntimeError(f"Backup already exists; review manually: {old}")
                    shutil.copytree(destination, old)
                    originals.append((destination, old))
                else:
                    originals.append((destination, None))
                replacement = Path(temp) / (name + "-ready")
                shutil.copytree(source[name], replacement)
                if destination.exists():
                    shutil.rmtree(destination)
                shutil.move(str(replacement), str(destination))
            pending = {"database": DB, "commit": commit, "modules": wanted, "backup": str(backup)}
            save(PENDING, pending)
        except Exception:
            for destination, old in reversed(originals):
                if destination.exists():
                    shutil.rmtree(destination)
                if old:
                    shutil.copytree(old, destination)
            raise
        print("\nPending: " + ", ".join(sorted(wanted)))
        print("Git commit: " + commit)
        print("Source backup: " + str(backup))
        print("Restart odoo18, reconnect, then run python3 /mnt/sethDeploy.py")
        return 10


def deploy():
    if not PENDING.exists():
        print("Nothing pending. Run /mnt/fsmupdate.sh to check GitHub first.")
        return 0
    pending = load(PENDING, {})
    if pending["database"] != DB:
        raise RuntimeError("Pending deployment belongs to another database")
    previous_pending = load(PENDING, {"database": DB, "modules": {}})
    if previous_pending.get("database") != DB:
        raise RuntimeError("Pending deployment belongs to another database")

    unfinished = set(previous_pending.get("modules", {}))
    for name, expected in pending["modules"].items():
        if digest(ADDONS / name) != expected:
            raise RuntimeError(f"Files for {name} changed after preparation. Pending list retained; review files before continuing.")
    print("Pending Git commit: " + pending["commit"])
    print("Modules: " + ", ".join(sorted(pending["modules"])))
    if input("Has odoo18 restarted since these files were copied? [yes/no]: ").strip().lower() not in {"y", "yes"}:
        print("Restart odoo18 first. Pending list retained.")
        return 1
    call = connect()
    live = installed(call)
    names = sorted(n for n in pending["modules"] if n in live)
    for name in sorted(set(pending["modules"]) - set(names)):
        print(f"SKIP no longer installed: {name}")
    if names:
        print("Upgrading: " + ", ".join(names), flush=True)
        call("ir.module.module", "button_immediate_upgrade", [live[n] for n in names])
    active = {r["code"] for r in call("res.lang", "search_read", [["active", "=", True]], fields=["code"])} if names else set()
    errors = []
    count = 0
    for name in names:
        for po in sorted((ADDONS / name / "i18n").glob("*.po")):
            lang = po.stem
            if lang not in active:
                print(f"SKIP inactive/unmatched language: {name}/{po.name}")
                continue
            try:
                record = call("base.language.import", "create", {
                    "name": lang, "code": lang,
                    "data": base64.b64encode(po.read_bytes()).decode("ascii"),
                    "filename": po.name, "overwrite": True,
                })
                call("base.language.import", "import_lang", [record])
                count += 1
                print(f"Imported: {name}/{po.name}")
            except Exception as exc:
                errors.append(str(po))
                print(f"FAILED {po}: {exc}")
    if errors:
        print("Translation import failed. Pending list retained; fix errors and rerun.")
        return 1
    baseline = load(BASELINE, {"database": DB, "modules": {}})
    if baseline.get("database") != DB:
        raise RuntimeError("Saved deployment state belongs to another database")
    baseline["modules"].update({n: pending["modules"][n] for n in names})
    baseline["commit"] = pending["commit"]
    save(BASELINE, baseline)
    PENDING.unlink()
    print(f"Success: {len(names)} module(s) upgraded, {count} PO file(s) imported.")
    print("Deployment baseline saved. Refresh your browser.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true", help="Fetch GitHub and stage changed installed modules")
    args = parser.parse_args()
    STATE.mkdir(parents=True, exist_ok=True)
    ADDONS.mkdir(parents=True, exist_ok=True)
    with (STATE / "lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another deployment script is already running")
        return prepare() if args.prepare else deploy()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("No successful deployment has been recorded for this attempt.", file=sys.stderr)
        sys.exit(1)
