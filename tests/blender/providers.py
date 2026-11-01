"""The provider layer without the internet: nothing waits for the network on the main thread,
errors are not swallowed, and downloads map HTTP errors the way the rest of the add-on expects.

The network is replaced by canned answers or by a small local server."""
import json
import os
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import bpy

MODULE = os.environ["ADDON_MODULE"]
checks = 0


def check(name, condition):
    global checks
    assert condition, name
    checks += 1
    print("PASS:", name)


def ensure_enabled_in_preferences():
    if MODULE not in bpy.context.preferences.addons:
        bpy.context.preferences.addons.new().module = MODULE


ensure_enabled_in_preferences()


def load(name):
    return __import__(f"{MODULE}.{name}", fromlist=["x"])


http = load("helpers.http")
asset_utils = load("apis.asset_utils")
constants = load("constants")
ph_item_module = load("apis.polyhaven.ph_asset_list_item")
ph_asset_module = load("apis.polyhaven.ph_asset")
acg_list_module = load("apis.ambient_cg.acg_asset_list")


class FakeNetwork:
    """Replaces http.get_json / http.iter_lines for the duration of a with block."""

    def __init__(self, json_answers=None, csv_lines=()):
        self.json_answers = json_answers or {}
        self.csv_lines = csv_lines
        self.json_calls = []

    def get_json(self, url, timeout=30):
        self.json_calls.append(url)
        for prefix, answer in self.json_answers.items():
            if url.startswith(prefix):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError(f"unexpected request: {url}")

    def iter_lines(self, url, timeout=30, encoding="utf-8"):
        yield from self.csv_lines

    def __enter__(self):
        self.saved = http.get_json, http.iter_lines
        http.get_json, http.iter_lines = self.get_json, self.iter_lines
        return self

    def __exit__(self, *args):
        http.get_json, http.iter_lines = self.saved


# ---- Poly Haven -------------------------------------------------------------------------------

def ph_item(name, kind):
    data = {
        "name": name.title(), "type": kind, "authors": {"someone": "x"}, "categories": ["rock"],
        "tags": ["a"], "download_count": 5, "date_published": 1_600_000_000,
    }
    return ph_item_module.PH_AssetListItem(name, data)


FILES_URL = "https://api.polyhaven.com/files/"
MATERIAL_FILES = {"blend": {"1k": {"blend": {"url": "u0.blend", "size": 100, "include": {
    "a.jpg": {"url": "u1", "size": 10}, "b.jpg": {"url": "u2", "size": 20}}}}}}
HDRI_FILES = {"hdri": {"1k": {"exr": {"url": "sky.exr", "size": 7}}}}

with FakeNetwork({FILES_URL: MATERIAL_FILES}) as net:
    item = ph_item("rusty_plate", 1)
    asset = item.to_asset("1k", "APPEND_REUSE")
    check("creating an asset does no request", net.json_calls == [])
    check("a new asset is not ready", not asset.is_ready() and not item.has_files_data)

    asset.prepare()
    check("prepare fetches the file list once", net.json_calls == [FILES_URL + "rusty_plate"])
    check("the asset is ready afterwards", asset.is_ready())
    check("download size adds the included files", asset.get_download_size() == 30)

    second = item.to_asset("1k", "LINK")
    check("another asset of the same item is ready at once", second.is_ready())
    second.prepare()
    check("the list is not fetched again", len(net.json_calls) == 1)
    check("both see the same data", second.get_download_size() == 30)

with FakeNetwork({FILES_URL: HDRI_FILES}):
    hdri = ph_item("sky", 0).to_asset("1k", "APPEND_REUSE")
    hdri.prepare()
    check("hdri size", hdri.get_download_size() == 7)

with FakeNetwork({FILES_URL: MATERIAL_FILES}):
    item = ph_item("model_thing", 2)
    model = item.to_asset("1k", "APPEND_REUSE")
    model.prepare()
    check("model size includes the blend file", model.get_download_size() == 130)

# A failed fetch raises (so the download job reports it) and is retried later
with FakeNetwork({FILES_URL: OSError("offline")}) as net:
    item = ph_item("offline_thing", 1)
    asset = item.to_asset("1k", "APPEND_REUSE")
    try:
        asset.prepare()
        raised = False
    except OSError:
        raised = True
    check("a failed fetch raises", raised)
    check("a failed fetch is not cached", not item.has_files_data and not asset.is_ready())
    net.json_answers[FILES_URL] = MATERIAL_FILES
    asset.prepare()
    check("a later attempt works", asset.is_ready() and asset.get_download_size() == 30)

# Assets from lists that carry their details are always ready
check("the base asset class is ready by default", load("apis.asset_types").Asset.is_ready(object()) is True)

# ---- ambientCG --------------------------------------------------------------------------------

BASE = "https://ambientcg.com/api/v2/full_json"
CSV = ["assetId,quality,type,size\n", "A,1K-JPG,zip,100\n", "B,1K-JPG,zip,200\n", "C,2K-JPG,zip,300\n"]


def acg_answers(fail_offset=None):
    def page(offset, assets):
        return {f"{BASE}?include=statisticsData,tagData,dimensionsData&offset={offset}&limit=2": {"foundAssets": assets}}

    answers = {BASE + "?limit=5000": {"numberOfResults": 3, "searchQuery": {"limit": 2}}}
    answers.update(page(0, [{"assetId": "A"}, {"assetId": "B"}]))
    answers.update(page(2, [{"assetId": "C"}]))
    if fail_offset is not None:
        for url in list(answers):
            if f"offset={fail_offset}&" in url:
                answers[url] = OSError("page failed")
    return answers


with FakeNetwork(acg_answers(), CSV):
    data = acg_list_module.ACG_AssetList.get_data()
    check("all pages are collected", sorted(data) == ["A", "B", "C"])
    check("quality levels are joined", data["A"]["quality_levels"]["1K-JPG"] == {"size": 100, "file_type": "zip"})
    check("every asset has its levels", all("quality_levels" in entry for entry in data.values()))

with FakeNetwork(acg_answers(fail_offset=2), CSV):
    try:
        acg_list_module.ACG_AssetList.get_data()
        raised = False
    except OSError:
        raised = True
    check("a failed page is an error, not a silently smaller catalog", raised)

# ---- download_file against a local server --------------------------------------------------------

PAYLOAD = b"asset-bytes" * 5000


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        status = {"/ok": 200, "/gone": 404, "/busy": 503}.get(self.path, 500)
        body = PAYLOAD if status == 200 else b"error"
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"

with tempfile.TemporaryDirectory() as folder:
    path = asset_utils.download_file(f"{base}/ok", Path(folder) / "new_folder", "file.bin")
    check("download_file returns the path", path == Path(folder) / "new_folder" / "file.bin")
    check("download_file writes everything", path.read_bytes() == PAYLOAD)

    for url, expected in (("/gone", ConnectionError), ("/busy", constants.ServerError503)):
        try:
            asset_utils.download_file(base + url, Path(folder), "x.bin")
            got = None
        except Exception as error:
            got = type(error)
        check(f"{url} raises {expected.__name__}", got is expected)
    check("a failed download leaves no file", not (Path(folder) / "x.bin").exists())

server.shutdown()
print(f"ALL {checks} CHECKS PASSED")
