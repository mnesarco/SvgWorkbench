# Svg Workbench (WIP)

Dedicated workbench for imported svg geometry manipulation.

> [!CAUTION]
> This workbench is in early development, not released yet for prime usage.

## Features

- Import svg as static/dynamic geometry
- Import svg selected geometries by several query options
- Reinterpret imported geometries by several options
- Export with true non scaling hairline strokes
- Synchronize imported geometries with external svg file
- Allow custom svg origin for imported geometries
- Support of &lt;use xlink:href="... /&gt; (linked clones)
- Export/Import presets (preferences)

## Architecture

- Based on declarative fcapi
- Packaging based on pyproject.toml, uv and fcapi

## Notice

While the code of this project was basically written from scratch, it is based on the original importSVG.py file from the FreeCAD source code, licensed under LGPL-2.1-or-later. Some parts of the SVG parsing modules contain code from the original file.