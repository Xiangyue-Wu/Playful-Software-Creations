# RMPP ScreenBridge

RMPP ScreenBridge mirrors a selected Windows desktop region to a reMarkable Paper Pro and lets you use the Windows screen from the tablet. The release ZIP contains a ready-to-run Windows wizard and a separate uninstaller; Python does not need to be installed.

**How it works:** the wizard downloads and verifies the official XOVI, AppLoad, and VNSee packages on Windows, then transfers them to the RMPP over USB SSH. VNSee receives the Windows image from TightVNC through a reverse SSH tunnel. TightVNC stays on Windows loopback; the VNC port is not exposed to the LAN or Internet.

## Use the release ZIP

1. Download `RMPP-ScreenBridge-v0.1.0-win-x64.zip` from [Releases](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases) and extract it to a writable folder.
2. Make sure Windows has TightVNC Server 2.8.89 configured to listen only on `127.0.0.1:5900` and offer VNC security type 1 (no VNC password). The wizard keeps access local and carries the stream through encrypted USB SSH. Connect the RMPP by USB and enable USB SSH.
3. Double-click `启动安装器.cmd`. In the wizard, enter the device password and click **检测设备**, then follow the install and start prompts. The first run needs Internet access on Windows to fetch verified packages; the RMPP does not download software.
4. Save unsynced notes before approving any prompt that creates the device hashtab or restarts `xochitl`. After activation, open **VNSee asivery Test** from AppLoad.
5. To remove the device components, exit VNSee normally and double-click `卸载RMPP-ScreenBridge.cmd`.

## Supported setup and safety

- Tested profile: reMarkable Paper Pro, AArch64, firmware `3.29.0.153`; VNC framebuffer `1620×720`. The VNSee layout displays the left `960×720` region in landscape. Other firmware and frame sizes are not enabled.
- The project mirrors part of an existing Windows display; it does **not** create a virtual or extended Windows display.
- Before device changes, the wizard creates a local backup under `临时备份/RMPP` and displays its path and SHA-256. Backups may contain private notes and documents; never publish or share them. Unsaved in-memory note edits are not included.
- Device removal checks the project install receipt and file hashes. If the tablet is unavailable, VNSee is running, or files differ, removal stops rather than deleting uncertain files.
- The project does not change persistent systemd settings, rmtool state, Windows display topology, or TightVNC's loopback-only boundary. It is intended for controlled testing, not as a universal installer.

The release package includes the GPL-3.0-only integration license and upstream notices. See [LICENSE](LICENSE), [upstream credits](THIRD_PARTY.md), and [recovery notes](docs/RECOVERY.md). This project is not endorsed by reMarkable or the upstream maintainers.

[简体中文](README.zh-CN.md) · [Source code](https://github.com/Xiangyue-Wu/Playful-Software-Creations/tree/main/RMPP-ScreenBridge)
