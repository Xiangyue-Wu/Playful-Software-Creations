# RMPP ScreenBridge

RMPP ScreenBridge lets a reMarkable Paper Pro show and interact with a selected region of an existing Windows desktop using VNSee. A Windows wizard checks the device, prepares the required software, starts the stream, and provides a separate uninstaller.

**How it works:** the wizard downloads and verifies the required packages on Windows, then transfers them to the tablet over USB SSH. VNSee receives the Windows image from TightVNC through a reverse SSH tunnel. TightVNC remains bound to Windows loopback; VNC is not exposed to the LAN or Internet. Before device-changing operations, the wizard creates a local backup and checks the project install receipt before removal.

This mirrors part of an existing Windows display; it does **not** create a Windows virtual or extended display.

## Quick start

1. Download or clone this folder to a writable location on Windows 11.
2. Install Python 3.10 or later and TightVNC Server 2.8.89. Configure TightVNC to listen only on `127.0.0.1:5900` and provide the VNC security mode required by the wizard.
3. Enable USB SSH on the RMPP and connect it to the PC.
4. Run [`启动安装器.cmd`](启动安装器.cmd). The project creates its own Python virtual environment and installs the pinned Python dependencies.
5. In the wizard, enter the USB SSH connection details, click **检测设备**, then follow the install and start prompts. Save unsynced notes before approving any operation that restarts `xochitl`.
6. Open **VNSee asivery Test** from AppLoad. To remove the device components, exit VNSee normally and run [`卸载RMPP-ScreenBridge.cmd`](卸载RMPP-ScreenBridge.cmd).

The tested setup uses a `1620×720` VNC framebuffer. Its VNSee-specific layout shows the left `960×720` region in a maximized landscape window. Other firmware versions and framebuffer sizes are not enabled by this profile.

## Safety and limitations

- Supported profile: reMarkable Paper Pro, AArch64, firmware `3.29.0.153`. The wizard rejects other firmware versions and unknown XOVI/runtime states.
- XOVI, AppLoad, VNSee, and TightVNC binaries are not included in this repository. Official packages are downloaded and verified on Windows; the RMPP receives files over USB SSH and does not download them.
- SSH host keys are checked and saved in the Windows user's `known_hosts`. An optional SSH password is stored with Windows Credential Manager, not as plaintext in the project. Do not share credentials or device backups.
- Before device changes, the wizard saves a scoped backup under `临时备份/RMPP` and displays its path and SHA-256. Backups may contain private notes and documents; they are Git-ignored and must not be published. Save notes before restarting `xochitl`; unsaved in-memory edits are not part of the backup.
- Device removal is receipt- and hash-checked. If the tablet is unreachable, VNSee is running, or installed files differ from the receipt, the uninstaller stops rather than deleting uncertain files. Remote removal cannot be guaranteed if the tablet or USB SSH is unavailable.
- The project does not change persistent systemd settings, rmtool state, Windows display topology, or TightVNC's loopback-only boundary.
- This is a controlled-testing tool for the profile above, not a universal or unattended installer. See [recovery notes](docs/RECOVERY.md) and [publication review](PUBLICATION_REVIEW.md).

## License and upstream projects

The integration code is GPL-3.0-only; see [LICENSE](LICENSE). VNSee, AppLoad, XOVI, Vellum packages, and TightVNC retain their respective licenses and authorship. See [upstream credits](THIRD_PARTY.md). This project is not endorsed by reMarkable or the upstream maintainers.

[简体中文](README.zh-CN.md)
