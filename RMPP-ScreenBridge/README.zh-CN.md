# RMPP ScreenBridge

RMPP ScreenBridge 把 Windows 屏幕选定区域投到 reMarkable Paper Pro（RMPP），并让用户在平板上操作 Windows 画面。Windows x64 Release ZIP 内含向导和独立卸载器，无需单独安装 Python。

**实现方式：** 向导在 Windows 下载并验证官方 XOVI、AppLoad、VNSee 软件包，经 USB SSH 传给 RMPP。若 Windows 没有 TightVNC Server，向导会下载官方签名安装包并按本项目配置安装 Server-only。VNSee 通过受限于本机访问的 TightVNC 和加密 USB SSH 反向隧道接收画面。

## 使用 Release ZIP

1. 从 [Releases](https://github.com/Xiangyue-Wu/Playful-Software-Creations/releases) 下载 `RMPP-ScreenBridge-v0.1.3-win-x64.zip`，解压到可写目录。
2. 通过 USB 连接 RMPP 并启用 USB SSH。首次启动需要 Windows 联网；RMPP 不联网下载。
3. 双击 `启动安装器.cmd`，输入设备密码，点击“一键准备并开始投屏”。前端检测设备，按需下载、验证并离线安装组件。若发现 TightVNC 旧安装记录但服务已丢失，会先显示产品记录，再用 Windows UAC 修复/升级官方 Server-only 组件；安装不添加防火墙例外，关闭 Web 访问和 VNC 密码认证，并启用 loopback-only 访问策略。
4. 首次安装、生成设备 hashtab 或启动 XOVI 前，先保存 RMPP 未同步笔记。向导会先将设备数据备份到电脑项目目录，并在重启 `xochitl` 前请求确认。完成后，在 AppLoad 中启动 **VNSee asivery Test**。
5. 退出 VNSee 后，可双击 `卸载RMPP-ScreenBridge.cmd`。卸载器按设备收据和文件哈希移除本项目安装的设备文件；若本项目曾自动安装 TightVNC，也可在 Windows 卸载器中选择移除它。

## 支持范围与安全

- 已验证配置：reMarkable Paper Pro、AArch64、固件 `3.29.0.153`；VNC framebuffer `1620×720`。VNSee 布局在横屏时显示左侧 `960×720` 区域。其他固件和尺寸暂不支持。
- 项目镜像现有 Windows 显示器区域，不创建虚拟显示器或扩展屏幕。
- TightVNC 使用自身的 loopback-only 访问策略，安装时不添加防火墙例外；向导核验服务 PID、实际监听地址、Web 端口，并通过本机回环验证 RFB。数据经加密 SSH 隧道传输。
- 每次设备变更前，向导先把 RMPP 笔记/文档、相关配置和软件备份至本机 `临时备份/RMPP`，并显示路径和 SHA-256。备份可能含私人文档，勿上传或分享；尚未保存到磁盘的笔记编辑不在备份内。
- TightVNC 卸载仅在本机安装收据、版本、服务路径和程序哈希全部匹配时执行。若安装前已有 TightVNC 产品，卸载器只移除本项目加入的 Server 功能；不会卸载原先存在的 Viewer/产品。
- 设备卸载会核验本项目安装收据和文件哈希。设备不可连接、VNSee 仍运行或文件不符时，停止删除不确定文件。
- 项目不修改持久 systemd 配置、rmtool 状态或 Windows 显示器拓扑。它面向已验证设备的受控测试，不是通用安装器。

Release ZIP 内含 GPL-3.0-only 集成代码许可和上游声明，见 [LICENSE](LICENSE)、[上游项目说明](THIRD_PARTY.md)及[恢复说明](docs/RECOVERY.md)。本项目未获 reMarkable 或上游维护者背书。

[English](README.md) · [源码](https://github.com/Xiangyue-Wu/Playful-Software-Creations/tree/main/RMPP-ScreenBridge)
