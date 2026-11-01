# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Asset Bridge Fork is an unofficial fork of Asset Bridge by Andrew Stevenson
# (https://github.com/strike-digital/asset_bridge), released under the same
# license. See NOTICE.md in the repository for what was changed.

bl_info = {
    "name": "Asset Bridge Fork",
    "author": "Andrew Stevenson (original), ziazarenda (fork)",
    "description": "Download free assets from Poly Haven and ambientCG into the asset browser (unofficial fork of Asset Bridge).",
    "blender": (5, 2, 0),
    "version": (2, 3, 0),
    "location": "3D View > N-Panel > Asset Bridge Fork",
    "warning": "",
    "doc_url": "https://github.com/ziazarenda/asset_bridge-fork",
    "category": "3D View",
}

from . import auto_load
from . import addon_updater_ops

auto_load.init()


def register():
    addon_updater_ops.register(bl_info)
    auto_load.register()


def unregister():
    auto_load.unregister()
    addon_updater_ops.unregister()
