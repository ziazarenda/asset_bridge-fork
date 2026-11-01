"""DownloadJob: a failed reload gives the previous files back.

    python tests/plain/download_job.py
"""
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ab_downloads", ROOT / "asset_bridge_fork" / "helpers" / "downloads.py")
downloads = importlib.util.module_from_spec(spec)
spec.loader.exec_module(downloads)

checks = 0


def check(name, condition):
    global checks
    assert condition, name
    checks += 1
    print("PASS:", name)


def run(directory, download, old_files):
    job = downloads.DownloadJob(directory, download, old_files).start()
    job.thread.join(10)
    return job


def listing(directory):
    return sorted(str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file())


with tempfile.TemporaryDirectory() as folder:
    # A first download that works
    directory = Path(folder) / "asset" / "1k"
    job = run(directory, lambda: (directory / "a.png").write_bytes(b"new"), [])
    check("a first download works", job.error is None and (directory / "a.png").read_bytes() == b"new")
    check("no incomplete marker is left after success", listing(directory) == ["a.png"])

    # A first download that fails stays incomplete
    broken = Path(folder) / "asset" / "2k"

    def fail_first():
        (broken / "part.png").write_bytes(b"half")
        raise OSError("network down")

    job = run(broken, fail_first, [])
    check("a failed first download reports the error", isinstance(job.error, OSError))
    check("a failed first download stays marked incomplete", (broken / downloads.INCOMPLETE_MARKER).exists())

    # A reload that works replaces the old files and removes the backups
    directory = Path(folder) / "reload" / "1k"
    (directory / "textures").mkdir(parents=True)
    old_a, old_b = directory / "a.png", directory / "textures" / "b.png"
    old_a.write_bytes(b"old-a")
    old_b.write_bytes(b"old-b")
    backup_dir = directory.with_name(directory.name + downloads.BACKUP_SUFFIX)

    def good_reload():
        check("the old files are kept aside while downloading", (backup_dir / "a.png").read_bytes() == b"old-a")
        old_a.write_bytes(b"new-a")
        old_b.write_bytes(b"new-b")

    job = run(directory, good_reload, [old_a, old_b])
    check("a good reload has no error", job.error is None)
    check("a good reload keeps the new files", old_a.read_bytes() == b"new-a" and old_b.read_bytes() == b"new-b")
    check("a good reload removes the backups", not backup_dir.exists())
    check("a good reload removes the incomplete marker", not (directory / downloads.INCOMPLETE_MARKER).exists())

    # A reload that fails gives the old files back
    directory = Path(folder) / "failing" / "1k"
    (directory / "textures").mkdir(parents=True)
    old_a, old_b = directory / "a.png", directory / "textures" / "b.png"
    old_a.write_bytes(b"old-a")
    old_b.write_bytes(b"old-b")
    backup_dir = directory.with_name(directory.name + downloads.BACKUP_SUFFIX)

    def bad_reload():
        old_a.write_bytes(b"half-written")
        (directory / "extra.png").write_bytes(b"half")
        raise OSError("network down")

    job = run(directory, bad_reload, [old_a, old_b])
    check("a failed reload reports the error", isinstance(job.error, OSError))
    check("a failed reload brings back the old files", old_a.read_bytes() == b"old-a" and old_b.read_bytes() == b"old-b")
    check("a failed reload leaves the old version usable (no marker)", not (directory / downloads.INCOMPLETE_MARKER).exists())
    check("a failed reload removes the backups", not backup_dir.exists())

    # The job is always reported as done
    check("the job is marked done after a failure", job.done.is_set())

print(f"ALL {checks} CHECKS PASSED")
