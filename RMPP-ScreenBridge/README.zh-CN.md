# RMPP ScreenBridge

RMPP ScreenBridge 让 reMarkable Paper Pro 通过 VNSee 显示并操作 Windows 桌面的一块区域。Windows 向导负责检测设备、准备所需软件、启动投屏，并提供独立卸载器。

**实现方式：** 向导在 Windows 下载并验证所需软件包，再通过 USB SSH 传到 RMPP；VNSee 通过 SSH 反向隧道，从 TightVNC 获取 Windows 画面。TightVNC 只监听 Windows 本机 `127.0.0.1`，VNC 端口不会开放给局域网或互联网。设备变更前，向导会在电脑本地创建备份；卸载时则依据安装收据和文件哈希核对项目文件。

本项目镜像的是现有 Windows 显示器区域，**不会创建 Windows 虚拟显示器或扩展屏幕**。

## 快速开始

1. 将本目录下载或克隆到 Windows 11 的可写位置。
2. 安装 Python 3.10 或更高版本、TightVNC Server 2.8.89。将 TightVNC 配置为只监听 `127.0.0.1:5900`，并使用向导要求的 VNC 安全模式。
3. 在 RMPP 启用 USB SSH，并通过 USB 连接电脑。
4. 运行 [`启动安装器.cmd`](启动安装器.cmd)。项目会创建独立 Python 虚拟环境，并安装固定版本的 Python 依赖。
5. 在向导中填写 USB SSH 连接信息，点击“检测设备”，再按提示安装和启动。任何会重启 `xochitl` 的操作前，请先保存未同步的笔记。
6. 在 AppLoad 中打开 **VNSee asivery Test**。卸载设备端组件前，先正常退出 VNSee，再运行独立的 [`卸载RMPP-ScreenBridge.cmd`](卸载RMPP-ScreenBridge.cmd)。

已验证配置使用 `1620×720` 的 VNC framebuffer；VNSee 专用布局会在横屏最大化窗口中显示左侧 `960×720` 区域。当前配置不开放其他固件版本或 framebuffer 尺寸。

## 安全与限制

- 支持范围：reMarkable Paper Pro、AArch64、固件 `3.29.0.153`。向导会拒绝其他固件和无法识别的 XOVI/运行时状态。
- 本仓库不包含 XOVI、AppLoad、VNSee 或 TightVNC 二进制。向导在 Windows 下载并验证官方软件包，再通过 USB SSH 传给 RMPP；设备端不联网下载。
- SSH 主机密钥会校验并记录到当前 Windows 用户的 `known_hosts`。可选 SSH 密码由 Windows 凭据管理器保存，不以明文写入项目。不要分享凭据或设备备份。
- 设备变更前，向导会把限定范围的备份保存到 `临时备份/RMPP`，并显示路径和 SHA-256。备份可能含私人笔记和文档，目录已加入 Git 忽略规则，切勿上传或公开分享。重启 `xochitl` 前请保存笔记；尚未写入磁盘的编辑内容不会包含在备份中。
- 设备端卸载会核对安装收据和文件哈希。如果设备无法连接、VNSee 仍运行或文件与收据不符，卸载器会停止，避免删除无法确认的文件。设备或 USB SSH 不可用时，无法保证远程卸载。
- 项目不会修改持久 systemd 配置、rmtool 状态、Windows 显示器拓扑，也不会放宽 TightVNC 的 loopback 监听边界。
- 本项目面向上述配置的受控测试，不是适配所有设备的通用无人值守安装器。参见[恢复说明](docs/RECOVERY.md)和[发布检查](PUBLICATION_REVIEW.md)。

## 许可与上游项目

集成代码采用 GPL-3.0-only，见 [LICENSE](LICENSE)。VNSee、AppLoad、XOVI、Vellum 软件包和 TightVNC 保留各自的许可和作者信息，见[上游项目说明](THIRD_PARTY.md)。本项目未获 reMarkable 或上游维护者背书。

[English](README.md)
