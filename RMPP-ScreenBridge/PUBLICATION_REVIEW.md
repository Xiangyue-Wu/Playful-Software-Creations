# Publication review

The source is published in the `RMPP-ScreenBridge` directory of the public `Playful-Software-Creations` repository. It is a portable, guided installer for controlled testing, not a production-ready universal release.

## Implemented

- Project-local Python bootstrap and a Windows GUI with device preflight, offline download, install, hashtab generation, capture, reverse tunnel, stock recovery, receipt-based install/uninstall, and a standalone Windows cleanup/uninstall entry point.
- No hardcoded personal backup paths, device hashtab, Windows Python path, or private SSH key.
- Pinned official XOVI/AppLoad/VNSee releases; independent Vellum APK control signature and datahash verification using a pinned official public-key hash.
- Only firmware 3.29.0.153 / AArch64 accepted. Existing XOVI and unknown runtime mounts are refused. Device binary files are never published in this repository.
- Before each device mutation/restart/removal, the GUI streams a scoped notes/config/software snapshot to the local ignored `临时备份/RMPP` directory and blocks the operation if the archive is incomplete or local disk space is insufficient.

## Required before claiming a production one-click installer

1. Perform a **fresh-device** install, hashtab creation, VNSee display, stock restore, and uninstall cycle with the new portable code. The previous closed-loop test used the old device-specific launcher.
2. Test interrupted downloads, SSH loss during transfer, interrupted hashtab generation, and interrupted XOVI startup; document exact recovery outcomes.
3. Confirm runtime prerequisites on a clean Windows account: Python, TightVNC Server configuration, USB route, SSH host-key enrollment, and optional Windows Credential Manager.
4. Review QMD compatibility and rollback for each additional RMPP firmware before expanding the supported profile. The installer deliberately rejects other versions.
5. Keep the published tree free of personal logs, device archives, notes, credentials, and third-party binaries. The current repository snapshot excludes those materials.
6. Verify a generated backup by restoring it to a separate test location/device; the current uninstaller does not automatically restore a snapshot.

The current result is suitable for **local code review and controlled testing on the stated profile**. It must not be described as tested on every RMPP or as an unattended installer.

