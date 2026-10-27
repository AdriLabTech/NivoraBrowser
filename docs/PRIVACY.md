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

## 4. What a fresh profile contacts (observed)

`tools/nivora/net_audit.py` starts the built browser with an empty profile and no proxy, loads one
local page, and logs every host name the resolver is asked about; the list was the same after 120 s
and after 5 minutes (2026-10-27). **No Zen-operated host appears.** What does appear is Firefox's own
behavior, which Nivora has **not** changed:

| Host | What Firefox does there | Turned off by (not changed by Nivora) |
|---|---|---|
| `firefox.settings.services.mozilla.com` | Remote Settings: certificate and blocklist data | `services.settings.server` (needed for revocation data; not recommended to disable) |
| `aus5.mozilla.org` | Update service, used here for the media components below | `media.gmp-manager.updateEnabled` |
| `ciscobinary.openh264.org` | Download of Cisco's OpenH264 codec (WebRTC video) | `media.gmp-gmpopenh264.enabled` |
| `edgedl.me.gvt1.com`, `update.googleapis.com` | Download and update of Google's Widevine content decryption module (streaming DRM) | `media.gmp-widevinecdm.enabled`, `media.eme.enabled` |
| `location.services.mozilla.com` | Region lookup | `browser.region.update.enabled` |
| `push.services.mozilla.com` | Web Push connection | `dom.push.enabled` |
| `firefox-portal-detection.com`, `mozilla.cloudflare-dns.com`, `ipv4only.arpa` | Captive-portal and connectivity checks, DNS-over-HTTPS bootstrap, NAT64 probe | `network.captive-portal-service.enabled`, `network.connectivity-service.enabled` |
| `support.mozilla.org` | Resolved at start-up; trigger not identified | |
| `www.google.com` | The default search engine: speculative connection from the address bar | `browser.urlbar.speculativeConnect.enabled`, or another default search engine |

Each of these shows the user's IP address to the operator. Whether a privacy-first browser should
ship with the media-component downloads and the Google default turned off is a product decision for
the owner ([ROADMAP.md](ROADMAP.md)); Nivora keeps Firefox's behavior because disabling them removes DRM
video and H.264 calls, and because the specification forbids weakening or replacing Firefox's
mechanisms without a decision. The audit is a **host-name log of attempts**, not a packet capture: it does not
show what was sent, and in an environment with no network a feature that only runs after a successful
first contact is not seen.

## 5. What is not verified

- A packet capture of an idle and a browsing session, with real network access and over days.
- Safe Browsing (`safebrowsing.googleapis.com` or its replacement) did not appear in five minutes; it is
  expected after the first page load that needs a list update.
- The effect of building without Mozilla and Google API keys (location services, Safe Browsing key
  files are read from `~/.nivora-keys`; none ship) has not been tested.

## 6. Rules

A preference that reduces a protection must say so in its description. Any future feature that
sends data off the machine must say what is sent, to whom, and be off until the user turns it on.
