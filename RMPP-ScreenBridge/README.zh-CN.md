# RMPP ScreenBridge

RMPP ScreenBridge 可把 Windows 桌面选定区域镜像到 reMarkable Paper Pro，并在平板上操作 Windows 画面。Release ZIP 内含可直接运行的 Windows 向导和独立卸载器，无需安装 Python。

**实现方式：** 向导在 Windows 下载并验证官方 XOVI、AppLoad、VNSee 软件包，再通过 USB SSH 传给 RMPP。VNSee 经 SSH 反向隧道，从 TightVNC 获取 Windows 画面。TightVNC 只监听 Windows 本机 `127.0.0.1`，VNC 端口不会暴露到局域网或互联网。

## 使用 Release ZIP

1. 从 [Releases](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases) 下载 `RMPP-ScreenBridge-v0.1.0-win-x64.zip`，解压到可写目录。
2. Windows 需要安装 TightVNC Server 2.8.89，且只监听 `127.0.0.1:5900`，提供无 VNC 密码的安全类型 1。访问仍限于本机，画面通过加密 USB SSH 隧道传输。通过 USB 连接 RMPP 并启用 USB SSH。
3. 双击 `启动安装器.cmd`，在向导中输入设备密码，点击“检测设备”，再按提示安装和启动。首次运行需要 Windows 联网下载并验证软件包；RMPP 不会联网下载。
4. 确认生成设备 hashtab 或重启 `xochitl` 前，先保存未同步笔记。激活后，在 AppLoad 中打开 **VNSee asivery Test**。
5. 卸载设备端组件前，先正常退出 VNSee，再双击 `卸载RMPP-ScreenBridge.cmd`。

## 支持范围与安全

- 已测试配置：reMarkable Paper Pro、AArch64、固件 `3.29.0.153`；VNC framebuffer 为 `1620×720`。VNSee 布局在横屏时显示左侧 `960×720` 区域。其他固件和画面尺寸暂不支持。
- 本项目镜像的是现有 Windows 显示器区域，**不会创建 Windows 虚拟显示器或扩展屏幕**。
- 设备变更前，向导会在电脑本地 `临时备份/RMPP` 创建备份并显示路径和 SHA-256。备份可能包含私人笔记和文档，请勿上传或分享；尚未保存到磁盘的笔记编辑不在备份内。
- 设备端卸载会核对项目安装收据和文件哈希。设备无法连接、VNSee 仍运行或文件与收据不符时，卸载会停止，不删除无法确认的文件。
- 项目不会修改持久 systemd 配置、rmtool 状态、Windows 显示器拓扑，也不会放宽 TightVNC 的 loopback 监听边界。本项目面向受控测试，不是适配所有设备的通用安装器。

Release ZIP 内含 GPL-3.0-only 集成代码许可和上游声明，见 [LICENSE](LICENSE)、[上游项目说明](THIRD_PARTY.md)及[恢复说明](docs/RECOVERY.md)。本项目未获 reMarkable 或上游维护者背书。

[English](README.md) · [源码](https://github.com/Xiangyue-Wu/Playful-Software-Creations/tree/main/RMPP-ScreenBridge)
