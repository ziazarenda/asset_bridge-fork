from typing import TYPE_CHECKING
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from bpy.types import Context

from ..asset_types import Asset
from ..asset_types import AssetListItem as PH_AssetListItem
from ..asset_utils import (HDRI, MODEL, MATERIAL, import_hdri, import_model, download_file, import_material,
                           file_name_from_url)
from ...helpers.process import new_blender_process

if TYPE_CHECKING:
    from .ph_asset_list_item import PH_AssetListItem  # noqa F811


class PH_Asset(Asset):
    """The Poly Haven asset is a bit different because it sometimes needs to be created in order to
    get information about the available quality levels of the asset. As such, the quality_level and link_method
    arguments are optional here, as opposed to the others where they are required."""

    def __init__(self, asset_list_item: PH_AssetListItem, quality_level: str = "", link_method: str = ""):
        self.list_item = asset_list_item
        self.name = asset_list_item.ab_name
        self.idname = asset_list_item.ab_idname
        self.type = asset_list_item.ab_type

        self.quality_level = quality_level
        # if quality_level:
        if link_method:
            self.link_method = link_method

    @property
    def raw_data(self) -> dict:
        """The file list of this asset, from https://api.polyhaven.com/files/<name>.
        It is fetched once per asset and shared by every PH_Asset of the same list item.
        The first access waits for the network: call prepare() from a worker thread first."""
        return self.list_item.get_files_data()

    def is_ready(self) -> bool:
        return self.list_item.has_files_data

    def prepare(self):
        self.list_item.get_files_data()

    @property
    def downloads_path(self):
        return self.list_item.downloads_dir / self.quality_level

    def get_quality_data(self) -> dict[str, dict]:
        data = self.raw_data
        if self.type == HDRI:
            return data["hdri"]
        elif self.type in {MATERIAL, MODEL}:
            return data["blend"]

    def get_files_to_download(self, quality_level: str) -> list[dict]:
        data = self.get_quality_data()[quality_level]
        if self.type == HDRI:
            return [data["exr"]]
        else:
            files = []
            files = list(data["blend"]["include"].values())
            if self.type == MODEL:
                files.append(data["blend"])
            return files

    def get_download_size(self):
        return sum([f["size"] for f in self.get_files_to_download(self.quality_level)])

    def download_asset(self):
        if not self.quality_level:
            raise ValueError(f"Cannot download {self.name} without providing a quality level")

        urls = self.get_files_to_download(self.quality_level)
        urls = [f["url"] for f in urls]
        paths: list[Path] = []
        for url in urls:
            if self.type == MODEL and not url.endswith(".blend"):
                paths.append(self.download_dir / "textures")
            else:
                paths.append(self.download_dir)

        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="AssetBridgeFile") as pool:
            futures = []
            for path, url in zip(paths, urls):
                path.mkdir(parents=True, exist_ok=True)
                name = file_name_from_url(url) if not url.endswith(".blend") else self.name + ".blend"
                futures.append(pool.submit(download_file, url, path, name))
            for future in futures:
                future.result()

        # Process the downloaded blend file if needed
        if self.type == MODEL:

            blend_file = [f for f in self.get_files() if f.suffix == ".blend"][0]
            print(self.idname)
            process = new_blender_process(
                script=Path(__file__).parent / "scripts" / "ph_sc_setup_asset.py",
                script_args=("--name", self.name, "--import_name", self.import_name),
                file=blend_file,
                use_stdout=True,
            )

            stdout, _ = process.communicate()
            out = stdout.decode(errors="replace")
            if process.returncode:
                raise RuntimeError(f"Error setting up Poly Haven asset blend file:\n{out}")

    def import_asset(self, context: Context):
        files = self.get_files()

        if self.type == HDRI:
            image_file = files[0]
            world = import_hdri(image_file, name=self.import_name, link_method=self.link_method)
            context.scene.world = world
            return world

        elif self.type == MATERIAL:
            # Find the files and add them to the dictionary with the correct keys for importing
            texture_files = {}
            files = {f.stem: f for f in files}
            associations = {
                "diffuse": {"diff", "col_1", "coll1", "col", "col_01"},
                "displacement": {"disp"},
                "normal": {"nor_gl"},
                "roughness": {"rough"},
            }

            for name, ph_names in associations.items():
                for ph_name in ph_names:
                    file = files.get(f"{self.name}_{ph_name}_{self.quality_level}")
                    if file:
                        texture_files[name] = file

            mat = import_material(texture_files, self.import_name, link_method=self.link_method)
            return mat

        elif self.type == MODEL:
            blend_file = [f for f in files if str(f).endswith(".blend")][0]
            imported = import_model(context, blend_file, name=self.import_name, link_method=self.link_method)
            return imported
