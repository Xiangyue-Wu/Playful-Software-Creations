# RMPP ScreenBridge（实验版）

[English](README.md) · [上游项目和许可](THIRD_PARTY.md)

Windows 向导从官方地址下载 XOVI v19、AppLoad 0.6.0、Vellum 的 asivery VNSee 1.1.1-r0，核对固定大小与 SHA-256，并独立验证 VNSee APK 的 RSA 签名和 payload 哈希。下载都在 Windows 完成，RMPP 仅通过 USB SSH 接收离线文件。安装收据记录每个文件的哈希，卸载时逐一复核。

**适用范围：** reMarkable Paper Pro、AArch64、固件 **3.29.0.153**。其他固件会被拒绝。源码包不含 VNSee、XOVI、AppLoad、TightVNC 的二进制，也不含笔记、密钥、密码或设备 hashtab。

## 准备条件

- Windows 11 已安装 Python 3.10+。双击 [`启动安装器.cmd`](启动安装器.cmd) 会在项目内建立 `.venv`，仅在 Windows 下载 Python 依赖。
- TightVNC Server 2.8.89 已作为服务安装，5900 **只监听 127.0.0.1**，提供 RFB 无密码类型 1。加密和外部访问边界由 USB SSH 隧道提供；若监听了其他网卡，向导会拒绝投屏。
- 已开启 RMPP USB SSH。首次连接时向导会记录设备主机密钥到 Windows `~/.ssh/known_hosts`；之后密钥变化会拒绝连接。
- RMPP 的 stock xochitl 正常运行，`/home/root/xovi` 不存在。若存在 rmtool，其 XOVI 必须已停用；向导不会更改 rmtool 状态。
- 已实测的 VNC framebuffer 是 **1620×720**。QMD 仅在 VNSee asivery Test 横屏最大化窗口显示左侧 960×720；其他尺寸未开放。

## 操作

1. 双击“启动安装器.cmd”，输入 RMPP USB IP 和 root SSH 密码。可选用 Windows 凭据管理器保存密码。
2. 点击“检测设备”，再点击“一键安装离线文件”。保存未同步笔记后，确认在**本机 RMPP**生成 hashtab；设备可能要求输入设备密码。若此时取消，文件保留但不能启动 XOVI，可稍后点击“生成/核对设备 hashtab”。不会接受手工复制的其他设备 hashtab。
3. 点击“连接并开始投屏”，保存笔记后确认临时重启 xochitl。保持 Windows 向导打开，在 RMPP AppLoad 中选择“VNSee asivery Test”。
4. 从 AppLoad 正常退出 VNSee；需要卸载时双击独立的 [`卸载RMPP-ScreenBridge.cmd`](卸载RMPP-ScreenBridge.cmd)。

这个方案复制 Windows 现有屏幕的一块区域，**不是虚拟扩展屏**。每次安装、生成设备 hashtab、启动/恢复 XOVI 或卸载前，都会先把笔记数据库、用户配置、本项目 XOVI/AppLoad/VNSee 文件、rmtool 和 xochitl 启动配置备份到 `临时备份\RMPP`；备份完成并校验后，前端会显示完整路径和 SHA256，备份失败则取消后续风险操作。备份不含系统分区镜像、SSH 私钥或尚未保存到磁盘的笔记编辑；重启 xochitl 前仍需先保存笔记。备份包含个人笔记，目录被 Git 忽略，严禁手动上传或公开分享。项目不修改持久 systemd、rmtool、笔记或 Windows 显示布局。

独立卸载器提供“卸载 RMPP + 清理 Windows 项目缓存”和“只清理 Windows 文件”两种操作。设备端只有在 USB SSH 可连接且本项目安装收据、文件哈希和 stock 状态均通过核对后才会删除；若设备离线、VNSee 尚在运行或文件被改动，卸载器会停止设备端删除并说明原因，可修复连接后重试。Windows 端只删除能按固定哈希/收据确认的本项目下载、安装包、日志和专用密码；默认安排在卸载器退出后删除项目 `.venv`，也可取消勾选。源码、卸载器、共享 SSH `known_hosts`、用户笔记备份、rmtool 和未知文件会保留。断电、系统损坏或 SSH 不可用时，无法远程保证设备端卸载；恢复路径见[说明](docs/RECOVERY.md)。

**新便携向导尚未在全新设备上完成安装、使用、卸载闭环测试。** 在完成该验证前，它属于实验版，不能宣称兼容所有固件。参见[发布前检查](PUBLICATION_REVIEW.md)。集成源码 GPL-3.0-only，上游许可见 [THIRD_PARTY.md](THIRD_PARTY.md)。

