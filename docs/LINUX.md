# Linux and Ryoku Arch

Linux is Nivora's first platform. This page says what works because Firefox and Zen already do
it, what is limited, and what is deliberately not done. Only an X11 session (Xvfb in a container)
has been used so far; **Wayland, GNOME, KDE Plasma, Hyprland and Ryoku Arch have not been
tested**, so nothing below is a compatibility claim for them.

## 1. What comes from Firefox (unchanged)

| Concern | Behavior | Source |
|---|---|---|
| Toolkit | GTK 3 | Gecko |
| Wayland / X11 | Gecko picks the backend from the session | Gecko |
| File dialogs, URL handlers, settings, location | `widget.use-xdg-desktop-portal.file-picker`, `.mime-handler`, `.settings` and `.location` default to `2` (automatic) in Firefox 158. For the file picker, automatic means the portal inside Flatpak or when `GTK_USE_PORTAL=1`, and the native GTK dialog otherwise | `StaticPrefList.yaml` |
| Notifications, open-with, default browser | Firefox's GTK/D-Bus integration | Gecko |
| Native messaging through the portal | Off (`0`) | Gecko |

Nivora does not change these preferences. A user who wants portal dialogs outside Flatpak sets
`GTK_USE_PORTAL=1` or the preference to `1`; whether to ship that as a default on Arch is left to
the packaging decision in [DISTRIBUTION.md](DISTRIBUTION.md).

## 2. What Zen sets for GTK (inherited, `prefs/zen/gtk.yaml`)

- `widget.gtk.rounded-bottom-corners.enabled = true`.
- `zen.widget.linux.transparency = false`: no window transparency by default.
- Window controls are hidden in the sidebar layout (`zen.view.hide-window-controls = true`); the
  corner radius follows the GTK client-side titlebar radius (`env(-moz-gtk-csd-titlebar-radius)`).

## 3. Known Linux limits

- **Compact mode cannot track the pointer outside the window on Linux** (Zen's own comment in
  `ZenMouseTrackerInternal.h`: Wayland does not expose the global pointer, and there is no
  reliable X11 equivalent in use). Features that reveal the sidebar or toolbar from the screen
  edge fall back to timeouts. This is an upstream limitation, not a Nivora regression.
- Hardware video decoding, screen sharing and global menus depend on the system and were not
  tested.

## 4. Environment detection

Nivora adds none. The rule for any future integration: detect the **capability** (a portal service
on the session bus, a protocol the compositor advertises), never the distribution name or an
environment variable alone, and never require it. Nothing in Nivora changes global desktop
settings automatically.

## 5. Ryoku Arch

There is no Ryoku-specific code, and none is required. The design rule is that anything specific to
Ryoku Arch must be optional, off unless detected by capability, and must not add a dependency on
Ryoku tools when a standard Linux mechanism exists. The Obsidian Eclipse palette is monochrome and
dark and does not depend on a theme engine.

## 6. Desktop integration files

The `.desktop` entry, icons, MIME associations, the update policy file and the Arch package are in
[DISTRIBUTION.md](DISTRIBUTION.md).

## 7. Compatibility matrix (to be filled by testing)

| Environment | State |
|---|---|
| X11 under Xvfb, Ubuntu 24.04 container (GTK, Adwaita/Yaru) | **works**: builds, starts, browses a local page, passes Nivora's and a subset of Zen's browser tests ([TESTING.md](TESTING.md)); profile in `~/.config/nivora` |
| Wayland (sway, headless, software-rendered, Ubuntu 24.04 container) | **starts and renders** as a native Wayland client with application id `nivora` (`tools/nivora/smoke_wayland.py`); no input device, so interaction, clipboard, IME and GPU paths are untested |
| Arch Linux, Wayland | not tested |
| Arch Linux, X11 | not tested |
| Hyprland | not tested |
| GNOME / KDE Plasma | not tested |
| Ryoku Arch | not tested |
