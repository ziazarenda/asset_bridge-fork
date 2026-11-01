# SPDX-License-Identifier: GPL-3.0-or-later
"""File-only download jobs. No Blender context, tasks, operators or timers here."""

from pathlib import Path
import shutil
from threading import Event, Thread
from time import sleep
import traceback


INCOMPLETE_MARKER = ".asset_bridge-incomplete"
# Old files wait here, next to the download folder, while a reload runs.
BACKUP_SUFFIX = ".asset_bridge-old"


def _retry(action, *args):
    """Renderers can briefly keep a texture file open during reload, so retry a locked file."""
    for attempt in range(10):
        try:
            return action(*args)
        except PermissionError:
            if attempt == 9:
                raise
            sleep(0.05)


class DownloadJob:
    """Publish completion through an Event; Blender polls it on the main thread.

    Cancellation in the UI suppresses importing. It does not terminate a provider's
    HTTP request or subprocess. Keep the directory busy until the worker exits.
    """

    def __init__(self, directory, download, old_files=()):
        self.directory = Path(directory)
        self.download = download
        self.old_files = tuple(Path(file) for file in old_files)
        self.done = Event()
        self.error = None
        self.traceback = ""
        self.thread = None
        # Total bytes to download. The download function sets it as soon as it is known.
        self.size = None

    def start(self):
        self.thread = Thread(target=self._run, name="AssetBridgeDownload", daemon=True)
        self.thread.start()
        return self

    def _run(self):
        marker = self.directory / INCOMPLETE_MARKER
        backup_dir = self.directory.with_name(self.directory.name + BACKUP_SUFFIX)
        moved = []
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            marker.touch()
            # Keep the previous files until the new download has worked.
            for file in self.old_files:
                if not file.exists():
                    continue
                backup = backup_dir / file.relative_to(self.directory)
                backup.parent.mkdir(parents=True, exist_ok=True)
                _retry(file.replace, backup)
                moved.append((file, backup))
            self.download()
            marker.unlink(missing_ok=True)
            shutil.rmtree(backup_dir, ignore_errors=True)
        except Exception as error:
            self.error = error
            self.traceback = traceback.format_exc()
            # The previous version is complete again once every old file is back.
            if moved and self._restore(moved, backup_dir):
                marker.unlink(missing_ok=True)
        finally:
            self.done.set()

    @staticmethod
    def _restore(moved, backup_dir):
        """Put the old files back, replacing partial new ones. Return whether all came back."""
        restored = True
        for file, backup in reversed(moved):
            try:
                file.parent.mkdir(parents=True, exist_ok=True)
                _retry(backup.replace, file)
            except OSError:
                restored = False
        if restored:
            shutil.rmtree(backup_dir, ignore_errors=True)
        return restored
