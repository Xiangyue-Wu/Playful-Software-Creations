# RMPP ScreenBridge (experimental)

[简体中文](README.zh-CN.md) · [Upstream credits](THIRD_PARTY.md)

This Windows wizard downloads XOVI v19, AppLoad 0.6.0 and Vellum's asivery VNSee 1.1.1-r0 to Windows, verifies pinned size and SHA-256, checks the VNSee APK RSA signature and payload hash, and uploads a self-contained bundle through USB SSH. It records every installed file hash for guarded removal.

**Supported profile:** reMarkable Paper Pro, AArch64, firmware **3.29.0.153**. Other firmware versions are rejected. The original VNSee binary, XOVI, AppLoad and TightVNC are upstream software and are not bundled here.

## Prerequisites

- Windows 11 with Python 3.10+ already installed. `启动安装器.cmd` creates a local `.venv` and installs pinned Python dependencies on Windows.
- TightVNC Server 2.8.89 installed as a service, listening **only on 127.0.0.1:5900**, with RFB security type 1 available. The wizard refuses any non-loopback listener.
- RMPP USB SSH enabled and root password available. On first USB connection, the wizard records the host key in Windows `~/.ssh/known_hosts`; later changes are rejected.
- Stock xochitl running, `/home/root/xovi` absent. If rmtool is installed, its XOVI must already be disabled; this wizard never changes rmtool's state.
- The tested VNC framebuffer is **1620×720**. A VNSee-only QMD displays its left 960×720 region in a maximized landscape window. Other frame sizes are not enabled.

## Use

1. Extract this source tree to a writable folder and double-click [`启动安装器.cmd`](启动安装器.cmd).
2. Enter the RMPP USB IP and SSH password. Optional password storage uses Windows Credential Manager.
3. Click **检测设备**, then **一键安装离线文件**. The files are placed only under `/home/root/xovi`, plus a dedicated receipt directory. Save unsynced notes before approving the one-time XOVI hashtab generation; the tablet may ask for its device password.
4. Click **连接并开始投屏**. Save notes before approving a temporary xochitl restart. Keep the wizard open, then select **VNSee asivery Test** in AppLoad.
5. Exit VNSee normally, click **恢复 stock 界面**, then run the separate [`卸载RMPP-ScreenBridge.cmd`](卸载RMPP-ScreenBridge.cmd) when needed.

The hashtab is generated **on the target device** by the pinned XOVI tool. Its creation temporarily interrupts xochitl. If declined or interrupted, the files stay installed but activation is blocked. Use **生成/核对设备 hashtab** to retry; a hashtab copied manually from another tablet is not accepted.

This mirrors a region of an existing Windows display through TightVNC loopback → USB SSH reverse tunnel → RMPP VNSee/QTFB. It does **not** create a Windows virtual display. It does not modify persistent systemd settings, rmtool, notes or Windows display topology.

Before installation, device-specific hashtab generation, XOVI activation/restoration, or uninstall, the wizard streams a read-only snapshot of the notebook database, user config, this project's XOVI/AppLoad/VNSee files, rmtool, and the xochitl unit/drop-ins to `临时备份/RMPP`. It displays the completed path and SHA256; if backup fails, the risky action is cancelled. The snapshot excludes OS partitions, SSH private keys, and unsaved in-memory note edits, so save notes before xochitl restarts. Backups contain private documents, are Git-ignored, and must not be uploaded or shared.

The standalone uninstaller offers **RMPP uninstall + selected Windows cache cleanup** and **Windows-only cleanup**. Device files are removed only when USB SSH works and the project receipt, every file/symlink hash, and stock state match. If the device is offline, VNSee is still running, or files changed, device removal stops and can be retried after recovery. Windows cleanup removes only project downloads, the verified install bundle, project logs, and dedicated credentials; `.venv` removal is enabled by default and happens after the UI exits, but can be unchecked. Source, uninstaller, shared SSH `known_hosts`, user notes, rmtool, and unknown files are kept. Remote device removal cannot be guaranteed while the tablet is unreachable or damaged. See [recovery](docs/RECOVERY.md).

The new portable wizard has **not yet completed a fresh-device install/use/uninstall cycle**. Treat it as experimental until that verification passes. See [publication review](PUBLICATION_REVIEW.md) for remaining release work.

Integration source is GPL-3.0-only; see [LICENSE](LICENSE). Upstream software retains its own license and authorship in [THIRD_PARTY.md](THIRD_PARTY.md).

