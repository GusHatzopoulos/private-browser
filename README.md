# Private Browser

A privacy-focused desktop web browser built with Python and Qt WebEngine.

## Project Status

Early development.

## Run

```powershell
pip install -r requirements.txt
python src/private_browser/main.py
```

## Privacy controls

Open **⋮ → Privacy and connection…**.

- Advertising/tracker request blocking is enabled by default in every window.
  The bundled starter list contains 32 domains and also matches their subdomains.
- Pause blocking on the current hostname if a site breaks, or disable blocking
  for the window. Reload the page after changing these options.
- Import additional UTF-8 domain lists or hosts files (up to 20 MB). Imported
  domains are added to the built-in list. EasyList/Adblock syntax and cosmetic
  rules are not supported. Blocking options, exceptions, counters and imported
  lists last only for the window's session; they do not store browsing history.
- This is a domain blocker, not a complete ad-blocking engine. Same-domain ads,
  many video ads, first-party tracking and fingerprinting are not comprehensively
  covered. There are no automatic filter downloads or updates.

## Tor routing

1. Run a local Tor SOCKS service separately. This project does not bundle,
   download or start Tor. The usual port is `9050`; Tor Browser commonly uses
   `9150` while running and connected.
2. Select **Local Tor SOCKS proxy**, set the port, and save.
3. Close **all** browser windows and restart using `main.py`.
4. Open **Privacy and connection → Open Tor connection check** to verify the
   exit connection yourself. Selecting the mode alone does not verify Tor.

Routing applies to all windows in the process. Connection preferences are saved
using Qt's OS settings store (on Windows, under the current user's
`Software\Private Browser\Private Browser` registry key). They contain only
the routing mode and local port. No live switching occurs across active sessions.
An invalid saved configuration prevents startup rather than silently using the
system connection.

Tor mode uses an explicit SOCKS5 proxy on `127.0.0.1`, requests remote hostname
resolution, disables QUIC and requests that WebRTC avoid non-proxied UDP.
It removes Chromium's implicit loopback proxy bypass. An unavailable proxy causes
page loads to fail rather than falling back to a direct connection. Tests cover
HTTP loading through a local SOCKS5 server and the unavailable-proxy case.
Full DNS, WebRTC and OS-level traffic auditing has not been performed.

**This is not Tor Browser and does not offer its anonymity protections.**
See the [Tor Project guidance on other browsers](https://support.torproject.org/tor-browser/security/using-tor-with-other-browsers/).
The browser does not currently manage circuits, provide a new identity, or
implement Tor Browser's fingerprinting protections.

## VPN

**System connection / existing VPN** follows the operating system's routing and
proxy configuration. Connect your existing VPN with its own application first.
This project does not yet establish a VPN tunnel, verify its status or provide
a VPN kill switch. Provider-specific integration requires a selected provider
or a supported connection configuration.

## Tests

```powershell
python -m unittest discover -s tests -v
```

GUI tests require a desktop session and permission to launch Qt WebEngine child
processes. Routing tests use local servers and fresh browser processes, not Tor
relays or external websites.
