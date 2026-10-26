# Interface icons

The icons in this directory are generated from [Phosphor Icons](https://phosphoricons.com)
(MIT License, see `phosphor-LICENSE.txt`) by `tools/nivora/generate_icons.py`, using the mapping in
`tools/nivora/icons/map.json`. Do not edit them by hand.

The directory keeps the name `nucleo` and the file names Zen used, so the jar manifests that
package them stay unchanged and upstream merges stay simple. Zen's own icons here are made with
Nucleo, whose license does not allow redistribution; Nivora does not ship them.

To add an icon: add its name to `map.json`, then run

    npm pack @phosphor-icons/core && tar xzf phosphor-icons-core-*.tgz
    python3 tools/nivora/generate_icons.py --phosphor package/assets

`python3 tools/nivora/generate_icons.py --check` verifies the directory.
