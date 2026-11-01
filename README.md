# Asset Bridge Fork

Download free **CC0** assets from **Poly Haven** and **ambientCG** straight into Blender's asset browser: materials, HDRIs and 3D models, with previews, drag and drop, and a settings panel for the imported asset.

This is an unofficial, maintained fork of [Asset Bridge](https://github.com/strike-digital/asset_bridge) by Andrew Stevenson, kept working on current Blender. It is released under the same licence. See [NOTICE.md](NOTICE.md) for credits and what changed.

> **Blender 5.2** is the tested target.

[image: the Asset Bridge library in Blender's asset browser]

---

## Contents

- [Features](#features)
- [Installation](#installation)
- [First setup](#first-setup)
- [Using the assets](#using-the-assets)
- [The Asset settings panel](#the-asset-settings-panel)
- [Changing the quality of an asset](#changing-the-quality-of-an-asset)
- [Preferences](#preferences)
- [Updating](#updating)
- [Moving from the original Asset Bridge](#moving-from-the-original-asset-bridge)
- [Folder structure](#folder-structure)
- [Development](#development)
- [Licence and credits](#licence-and-credits)

---

## Features

- **Thousands of free assets** from Poly Haven and ambientCG, all CC0, browsed in Blender's own asset browser.
- **Previews first, downloads on demand.** The previews are downloaded once. An asset is only downloaded in full when you use it.
- **Drag and drop** materials, HDRIs and models into the scene.
- **Choose the quality** (resolution and format) per asset, and **change it later** without rebuilding the material.
- **Asset settings panel** in the 3D Viewport to tweak an imported material or HDRI.
- **Real-world scale** for materials.
- **Progress shown in the viewport** while an asset downloads, with a cancel button.
- **Does not freeze Blender** while it talks to the servers.
- **Updates itself** from this repository's releases.

---

## Installation

1. Download `asset_bridge_fork-x.y.z.zip` from the [Releases](../../releases) page.
2. In Blender open **Edit → Preferences → Add-ons**.
3. Open the drop-down in the top right, choose **Install from Disk…** and pick the zip.
4. Enable **Asset Bridge Fork**.

[image of the Install from Disk menu]

You need an internet connection to download the previews and the assets.

---

## First setup

1. In the add-on's preferences, choose a **library folder**. This is where previews and downloaded assets are kept, so pick a drive with enough space.
2. Press **Download asset previews**. The add-on fetches the asset lists, then the preview images (several thousand, so it takes a little while), and finally sets up the asset library.
3. The **Asset Bridge** library now appears in Blender's asset browser.

[image of the preferences with the Download asset previews button]

[gif of the first setup]

Later, **Check for new assets** looks for assets added since you last checked, and downloads their previews.

---

## Using the assets

Open an **Asset Browser** and choose the **Asset Bridge** library. The assets are sorted into catalogs: HDRIs, Materials and Models.

- **Drag an asset into the scene**, or into the 3D Viewport. Materials land on the object under the cursor, HDRIs become the world, and models are added to the scene.
- The first time you use an asset it is **downloaded**. A progress widget in the viewport shows the download and has a cancel button.
- The asset browser's sidebar shows information about the selected asset (author, links, number of downloads, tags) and a **Quality** drop-down, with the file size next to each quality.
- The **Import settings** decide how the asset is brought in, for example whether materials get real-world scale and which collection new models go into.
- To download an asset again, use the **refresh button** next to its name.

[image of the asset browser sidebar with Quality]

[gif of dragging a material onto an object]

---

## The Asset settings panel

When an imported material, HDRI or model is selected, a **Asset settings** panel appears in the 3D Viewport sidebar. The tab is named **Asset Bridge Fork** by default and can be changed in the preferences.

For materials it has these sections:

| Section | What it does |
|---------|--------------|
| **General** | Overall scale, normal strength and roughness |
| **Color** | Hue, saturation and value |
| **Mapping** | Location, scale and rotation of the texture |
| **Anti-Tiling** | Hides repeating patterns. A preview button shows the segments |
| **Displacement** | Height-map displacement, with scale and method |

HDRIs have **Color** and **Warping** sections.

[image of the Asset settings panel]

---

## Changing the quality of an asset

At the top right of the Asset settings panel there is a button that shows the **current quality**, for example `1k jpg`. Click it to open a list of all the qualities available for that asset:

- a checkmark means it is already downloaded,
- an import icon means it will be downloaded now,
- the current quality is greyed out.

Your changes to the settings (scale, colour and so on) are copied to the new version.

[image of the quality menu]

---

## Preferences

| Setting | What it does |
|---------|--------------|
| **Library folder** | Where previews, assets and the asset library are stored |
| **External downloads path** | Optional separate folder for downloaded files |
| **3D Viewport panel category** | The sidebar tab of the Asset settings panel. Leave it empty to turn the panel off |
| **Automatically pack files** | Pack imported images into the .blend file |
| **Download widget scale and speed** | Size and animation of the progress widget |
| **Auto-check for updates** | Checks this repository for new releases |

The menu next to **Check for new assets** has extra tools: redownload all previews, set the asset library up again, and open the preview folder.

---

## Updating

The add-on can check this repository for new releases. Turn on **Auto-check for updates** in the preferences, or use **Check now**. When a newer release exists, it offers to install it.

---

## Moving from the original Asset Bridge

1. Disable the original Asset Bridge first, so the two do not fight over the same library.
2. Install this add-on and point it to the same **library folder**. Your downloaded assets and previews keep working.

---

## Folder structure

```text
asset_bridge_fork/          the add-on (this is what ends up in the zip)
├── __init__.py             bl_info and register / unregister
├── auto_load.py            registers every Blender class automatically
├── constants.py            add-on id and GitHub details used by the updater
├── api.py                  the asset lists and their loading
├── settings.py             data stored in the .blend file
├── preferences.py          the Preferences panel
├── handlers.py             Blender event handlers
├── apis/                   the two asset providers
│   ├── polyhaven/          Poly Haven
│   ├── ambient_cg/         ambientCG
│   ├── asset_types.py      the shared asset classes
│   └── asset_utils.py      downloading and importing files
├── operators/              buttons: import, download previews, swap quality, ...
├── ui/                     the Asset Browser and 3D Viewport panels and menus
├── helpers/                small utilities: HTTP, downloads, progress, drawing, ...
├── scripts/                scripts run in a separate background Blender process
├── resources/icons/        icons
├── vendor/humanize/        third-party library (see NOTICE.md)
├── addon_updater.py        updater engine (from the kit)
└── addon_updater_ops.py    updater operators and UI (from the kit)
```

---

## Development

The build tooling comes from the shared [blender-addon-kit](https://github.com/ziazarenda/blender-addon-kit). Do not edit those files here.

```text
build.py        runs the tests, builds the zip, installs it into a temporary
                Blender profile and runs the Blender tests
tests/plain/    tests that run without Blender (package checks, HTTP, downloads)
tests/blender/  tests that run inside Blender (registration, materials, providers, GPU)
docs/           maintenance notes on the original code
.kit.json       records which files come from the kit
```

```bash
uv run python build.py                  # plain tests, build, Blender tests in a clean profile
uv run python build.py --skip-blender   # without Blender
uv run python build.py --headless       # skip tests that need a window
```

[image of a passing build in the terminal]

---

## Licence and credits

**GPL v3 or later**, the same as the original (see `LICENSE`). The original copyright header is kept in `asset_bridge_fork/__init__.py`.

- **Asset Bridge** by Andrew Stevenson, the original add-on. This fork is not made, endorsed or supported by him. If you want to support his work, see the [original project](https://github.com/strike-digital/asset_bridge).
- **Poly Haven** and **ambientCG** supply the assets, all under CC0.
- Third-party code is listed in [NOTICE.md](NOTICE.md).
