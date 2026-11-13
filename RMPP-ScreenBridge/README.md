# RMPP ScreenBridge

RMPP ScreenBridge mirrors a selected Windows screen region to a reMarkable Paper Pro (RMPP) and lets you use the Windows view on the tablet. The Windows x64 release ZIP includes a setup wizard and a separate uninstaller; Python is not required.

**How it works:** the wizard downloads and verifies the official XOVI, AppLoad, and VNSee packages on Windows, then transfers them over USB SSH. If TightVNC Server is absent, the wizard downloads its official signed installer and installs the server-only feature using this project's access settings. VNSee receives the screen through TightVNC and an encrypted reverse SSH tunnel.

## Use the release ZIP

1. Download `RMPP-ScreenBridge-v0.1.1-win-x64.zip` from [Releases](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases) and extract it to a writable folder.
2. Connect the RMPP by USB and enable USB SSH. Windows needs Internet access on first launch; the tablet does not download software.
3. Double-click `启动安装器.cmd`, enter the device password, and click **一键准备并开始投屏**. The wizard checks the device and downloads, verifies, and installs missing components. If TightVNC is needed, Windows prompts through UAC. The installer adds only the server, adds no firewall exception, disables Web access and VNC password authentication, and enables TightVNC's loopback-only access policy.
4. Save unsynced notes before creating the device hashtab or starting XOVI. The wizard backs up device data to the project folder before device changes and asks before restarting `xochitl`. When ready, launch **VNSee asivery Test** from AppLoad.
5. Exit VNSee before using `卸载RMPP-ScreenBridge.cmd`. The device uninstaller verifies the project receipt and file hashes. If this project installed TightVNC, the Windows uninstaller can remove it as well.

## Supported setup and safety

- Verified profile: reMarkable Paper Pro, AArch64, firmware `3.29.0.153`; VNC framebuffer `1620×720`. In landscape, the VNSee layout shows the left `960×720` region. Other firmware versions and frame sizes are not supported yet.
- The project mirrors an existing Windows display region; it does **not** create a virtual or extended Windows display.
- TightVNC uses its loopback-only access policy. The installer adds no firewall exception. Windows may report a wildcard socket binding, so the wizard also verifies the TightVNC service PID and policy settings, then checks RFB over local loopback. Image data travels through the encrypted SSH tunnel.
- Before each device change, the wizard backs up notes/documents, relevant settings, and project software to `临时备份/RMPP` on the Windows computer and displays the path and SHA-256. Backups can contain private documents; do not upload or share them. Unsaved in-memory edits are not included.
- TightVNC is removed only when the local install receipt, version, service path, and executable hash all match. A TightVNC installation that existed before this project is not removed.
- Device removal checks the project install receipt and file hashes. If the tablet is unavailable, VNSee is running, or files differ, removal stops rather than deleting uncertain files.
- The project does not change persistent systemd configuration, rmtool state, or Windows display topology. It is intended for controlled testing on the verified profile, not as a universal installer.

The release package includes the GPL-3.0-only integration license and upstream notices. See [LICENSE](LICENSE), [upstream credits](THIRD_PARTY.md), and [recovery notes](docs/RECOVERY.md). This project is not endorsed by reMarkable or upstream maintainers.

[简体中文](README.zh-CN.md) · [Source code](https://github.com/Xiangyue-Wu/Playful-Software-Creations/tree/main/RMPP-ScreenBridge)
