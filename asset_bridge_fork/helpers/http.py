"""Small HTTP client on the standard library. No Blender imports, so it can be tested alone.

Every call has a timeout, so a slow or dead server cannot hang a thread for ever.
The timeout applies to each wait on the socket (connecting, then each read), not to the
whole transfer: a big download that keeps making progress is never cut off.

Blocking calls must not run on Blender's main thread: use them from worker threads.
"""
import http.client
import json
import os
import shutil
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "asset_bridge_fork (https://github.com/ziazarenda/asset_bridge-fork)"
DEFAULT_TIMEOUT = 30


class HttpError(OSError):
    """The server answered with an error status (404, 503, ...)."""

    def __init__(self, url, status, reason=""):
        super().__init__(f"HTTP {status} {reason}".strip() + f" for {url}")
        self.url = url
        self.status = status
        self.reason = reason


def open_url(url, timeout=DEFAULT_TIMEOUT, method="GET"):
    """Open a URL and return the response (use it in a `with` block).

    Raises HttpError for an error status, and OSError (URLError, TimeoutError) when the
    server cannot be reached."""
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        error.close()
        raise HttpError(url, error.code, str(error.reason)) from None


def get_json(url, timeout=DEFAULT_TIMEOUT):
    with open_url(url, timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def iter_lines(url, timeout=DEFAULT_TIMEOUT, encoding="utf-8"):
    """Yield the decoded lines of a (possibly large) text response, without keeping it all."""
    with open_url(url, timeout) as response:
        for line in response:
            yield line.decode(encoding)


def download_to(url, destination, timeout=DEFAULT_TIMEOUT):
    """Download a file. It appears at `destination` only when it is complete.

    The data goes to a `.part` file first, which is renamed at the end and removed on any
    failure, so an interrupted download never leaves something that looks like the file."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")

    try:
        with open_url(url, timeout) as response, open(partial, "wb") as file:
            try:
                shutil.copyfileobj(response, file)
            except http.client.IncompleteRead as error:
                raise OSError(f"The connection closed before {url} was complete") from error

            expected = response.headers.get("Content-Length")
            if expected is not None and file.tell() != int(expected):
                raise OSError(f"Incomplete download of {url}: got {file.tell()} of {expected} bytes")
        os.replace(partial, destination)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise

    return destination


def is_online(url="https://www.google.com/", timeout=3):
    """Whether a server can be reached. Any answer counts, even an error status."""
    try:
        open_url(url, timeout, method="HEAD").close()
    except HttpError:
        return True
    except OSError:
        return False
    return True
