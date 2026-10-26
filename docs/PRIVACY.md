# Privacy

Nivora does not add telemetry, accounts, analytics or services of its own, and it does not
replace Firefox's protections with home-made ones. This document states what the browser does by
default, what Nivora changed, and what has not been verified. It makes no claim of anonymity, of
resistance to fingerprinting, or of freedom from network leaks.

## 1. Where the settings are

| Area | Where in the interface | Default, from Firefox 158 unless noted |
|---|---|---|
| Tracking protection | Settings > Privacy & Security | Enhanced Tracking Protection: Standard. Neither Zen nor Nivora changes `privacy.trackingprotection.*` |
| Cookies and site data | same; Clear data | Firefox defaults; `cookieBehavior` untouched |
| History | same | Remembered. Private windows do not record it |
| Private browsing | Menu, palette ("Open Private Window") | Firefox's. Zen adds `browser.privatebrowsing.forceMediaMemoryCache` |
| Site permissions (camera, microphone, location, notifications, devices) | Site information panel; Settings > Permissions | Ask each time. Unchanged |
| Certificates | Address bar padlock; Settings > Certificates | Firefox's; no change to validation |
| Downloads | Settings > General; panel | Firefox's, plus Zen's panel animation |
| Global Privacy Control | Settings > Privacy | **On** (`privacy.globalprivacycontrol.enabled`, set by Zen) |
| Containers | Settings; palette | UI enabled (`privacy.userContext.ui.enabled`, set by Zen) |

## 2. What Zen changes (inherited, `prefs/privatefox/`)

These come from Zen's own configuration and are kept:

- Telemetry and data reporting off at build time and by preference
  (`datareporting.*`, `toolkit.telemetry.*`, `browser.ping-centre.telemetry`, ...).
- Mozilla studies and experiments off (`app.shield.optoutstudies.enabled`, `app.normandy.*`;
  `app.normandy.api_url` emptied).
- Crash reports are not sent automatically.
- Mozilla promotion surfaces off (VPN promo, "More from Mozilla", add-on recommendations, welcome
  flow).
- `termsofuse.bypassNotification = true`: skips Mozilla's terms-of-use notification. **Legal
  review item**: Nivora should present its own terms position instead of silently inheriting this.

## 3. What Nivora changed

Everything in [SECURITY.md](SECURITY.md) section 4: no update host, share service, mods injection or
what's-new / welcome pages operated by the Zen project; the Library donate button and the mods
website link hidden by default. No preference was changed that lowers a Firefox protection.

## 4. What is not verified

- A traffic capture of an idle and a browsing session (test F-09) has not been run, so "no
  connection to Zen hosts" is true of the configuration, not yet of observed behavior.
- Firefox's own background services (Remote Settings, Safe Browsing, add-on and search endpoints,
  captive-portal and connectivity checks) work as in Firefox and have not been audited for this
  build.
- The effect of building without Mozilla and Google API keys (location services, Safe Browsing key
  files are read from `~/.nivora-keys`; none ship) has not been tested.

## 5. Rules

A preference that reduces a protection must say so in its description. Any future feature that
sends data off the machine must say what is sent, to whom, and be off until the user turns it on.
