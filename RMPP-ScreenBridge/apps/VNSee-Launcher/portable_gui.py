"""Windows setup wizard for the supported RMPP profile.

Never stores a plaintext password or accepts an unknown SSH host key.
"""
from __future__ import annotations

import json
import pathlib
import re
import socket
import subprocess
import threading
import tkinter as tk
import winreg
from tkinter import messagebox, ttk

import paramiko
import win32api
import win32cred

import portable_manager as manager

HOST_DEFAULT = "10.11.99.1"
KNOWN_HOSTS = pathlib.Path.home() / ".ssh" / "known_hosts"


def credential_target(host: str) -> str:
    return "RMPP-ScreenBridge:ssh:root@" + host


def legacy_credential_target(host: str) -> str:
    return "RMPP-VNSee-Portable:ssh:root@" + host


def saved_password(host: str) -> str:
    for target in (credential_target(host), legacy_credential_target(host)):
        try:
            value = win32cred.CredRead(target, win32cred.CRED_TYPE_GENERIC, 0)["CredentialBlob"]
            return value.decode("utf-16-le") if isinstance(value, bytes) else value
        except Exception:
            pass
    return ""


def save_password(host: str, password: str) -> None:
    win32cred.CredWrite({"Type": win32cred.CRED_TYPE_GENERIC,
                         "TargetName": credential_target(host), "UserName": "root",
                         "CredentialBlob": password, "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
                         "Comment": "RMPP VNSee USB SSH"}, 0)


def tightvnc_exe() -> pathlib.Path:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\tvnserver") as key:
            command = winreg.QueryValueEx(key, "ImagePath")[0]
    except OSError as exc:
        raise RuntimeError("没有安装 TightVNC Server 服务；请先安装官方 Server 2.8.89") from exc
    command = winreg.ExpandEnvironmentStrings(command).strip()
    match = re.match(r'^"([^"]+\.exe)"', command, re.I) or re.match(r'^(.+?\.exe)(?:\s|$)', command, re.I)
    if not match:
        raise RuntimeError("无法解析 TightVNC Server 服务的程序路径")
    path = pathlib.Path(match.group(1))
    if not path.is_file():
        raise RuntimeError(f"TightVNC 服务文件不存在：{path}")
    details = win32api.GetFileVersionInfo(str(path), "\\")
    ms, ls = details["FileVersionMS"], details["FileVersionLS"]
    version = (ms >> 16, ms & 0xFFFF, ls >> 16)
    if version != (2, 8, 89):
        raise RuntimeError(f"仅验证过 TightVNC Server 2.8.89；当前文件版本 {version}")
    return path


def vnc_loopback() -> None:
    query = ("$p=@(Get-NetTCPConnection -LocalPort 5900 -State Listen -ErrorAction SilentlyContinue | "
             "Select-Object LocalAddress,OwningProcess); $p | ConvertTo-Json -Compress")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", query],
                         capture_output=True, text=True, timeout=15, check=True).stdout.strip()
    rows = json.loads(out) if out else []
    if isinstance(rows, dict):
        rows = [rows]
    if not rows or "127.0.0.1" not in {row["LocalAddress"] for row in rows}:
        raise RuntimeError("TightVNC 尚未监听 Windows 127.0.0.1:5900")
    if any(row["LocalAddress"] not in ("127.0.0.1", "::1") for row in rows):
        raise RuntimeError("TCP 5900 对非本机网卡开放；请先关闭额外实例或限制监听")


def read_exact(sock: socket.socket, size: int) -> bytes:
    result = b""
    while len(result) < size:
        data = sock.recv(size - len(result))
        if not data:
            raise RuntimeError("VNC 握手中断")
        result += data
    return result


def rfb_size() -> tuple[int, int]:
    with socket.create_connection(("127.0.0.1", 5900), timeout=4) as sock:
        sock.settimeout(4)
        version = read_exact(sock, 12)
        if version != b"RFB 003.008\n":
            raise RuntimeError(f"VNC 协议版本未验证：{version!r}")
        sock.sendall(version)
        types = read_exact(sock, read_exact(sock, 1)[0])
        if 1 not in types:
            raise RuntimeError("VNC 未提供无密码类型 1；不会改动你的认证设置")
        sock.sendall(b"\x01")
        if read_exact(sock, 4) != b"\x00" * 4:
            raise RuntimeError("VNC 认证握手失败")
        sock.sendall(b"\x01")
        header = read_exact(sock, 24)
        return int.from_bytes(header[:2], "big"), int.from_bytes(header[2:4], "big")


def pipe(channel: paramiko.Channel) -> None:
    try:
        with socket.create_connection(("127.0.0.1", 5900), timeout=4) as local:
            channel.settimeout(1)
            local.settimeout(1)

            def transfer(src, dst):
                try:
                    while True:
                        try:
                            data = src.recv(65536)
                        except socket.timeout:
                            continue
                        if not data:
                            break
                        dst.sendall(data)
                except Exception:
                    pass
                finally:
                    try:
                        if isinstance(dst, socket.socket):
                            dst.shutdown(socket.SHUT_WR)
                        else:
                            dst.shutdown_write()
                    except Exception:
                        pass
            a = threading.Thread(target=transfer, args=(channel, local), daemon=True)
            b = threading.Thread(target=transfer, args=(local, channel), daemon=True)
            a.start()
            b.start()
            a.join()
            b.join()
    finally:
        channel.close()


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RMPP VNSee · 离线安装与投屏")
        self.root.geometry("650x580")
        self.root.minsize(570, 500)
        self.client = None
        self.forward = False
        self.busy = False
        self.host = tk.StringVar(value=HOST_DEFAULT)
        self.password = tk.StringVar(value=saved_password(HOST_DEFAULT))
        self.remember = tk.BooleanVar(value=bool(self.password.get()))
        self.host.trace_add("write", self.on_host_change)
        self.x = tk.StringVar(value="0")
        self.y = tk.StringVar(value="805")
        self.width = tk.StringVar(value="1620")
        self.height = tk.StringVar(value="720")
        self.status = tk.StringVar(value="仅验证过 RMPP 固件 3.29.0.153；每次风险操作前先把设备数据备份到本项目。")

        body = ttk.Frame(self.root, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="RMPP VNSee", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(body, text="Windows 下载并验证 → USB SSH 上传 → RMPP 离线安装", font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 15))
        form = ttk.Frame(body)
        form.pack(fill="x")
        for row, (title, var, secret) in enumerate((("RMPP USB IP", self.host, False), ("root SSH 密码", self.password, True))):
            ttk.Label(form, text=title).grid(row=row, column=0, sticky="w", pady=5)
            ttk.Entry(form, textvariable=var, show="*" if secret else "", width=34).grid(row=row, column=1, sticky="ew", padx=10)
        form.columnconfigure(1, weight=1)
        credentials = ttk.Frame(body)
        credentials.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(credentials, text="使用 Windows 凭据管理器保存 SSH 密码", variable=self.remember).pack(side="left")
        ttk.Button(credentials, text="删除已存密码", command=self.forget_password).pack(side="right")
        capture = ttk.LabelFrame(body, text="Windows 捕获区域（已验证：1620 × 720）", padding=10)
        capture.pack(fill="x", pady=14)
        for col, (name, value) in enumerate((("X", self.x), ("Y", self.y), ("宽", self.width), ("高", self.height))):
            ttk.Label(capture, text=name).grid(row=0, column=col, sticky="w")
            ttk.Entry(capture, textvariable=value, width=10).grid(row=1, column=col, sticky="ew", padx=(0, 8))
            capture.columnconfigure(col, weight=1)
        ttk.Button(capture, text="恢复默认：0, 805, 1620 × 720", command=self.reset_capture).grid(
            row=2, column=0, columnspan=4, sticky="ew", pady=(9, 0))
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=5)
        for row, label, action in (
            (0, "检测设备", self.check),
            (1, "一键安装离线文件", self.install),
            (2, "生成/核对设备 hashtab", self.complete),
            (3, "连接并开始投屏", self.start),
            (4, "恢复 stock 界面", self.restore),
            (5, "卸载本程序安装的文件", self.uninstall),
            (6, "备份当前 RMPP 到临时备份", self.backup_device),
        ):
            ttk.Button(actions, text=label, command=action).grid(row=row // 2, column=row % 2, sticky="ew", padx=4, pady=4)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        ttk.Label(body, text="状态与错误（可选中复制）").pack(anchor="w", pady=(12, 4))
        self.output = tk.Text(body, height=7, wrap="word")
        self.output.pack(fill="both", expand=True)
        self.output.insert("end", self.status.get())
        self.output.configure(state="disabled")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def show(self, text: str):
        def update():
            self.output.configure(state="normal")
            self.output.insert("end", "\n" + text)
            self.output.see("end")
            self.output.configure(state="disabled")
            self.status.set(text)
        self.root.after(0, update)

    def reset_capture(self):
        for variable, value in ((self.x, "0"), (self.y, "805"), (self.width, "1620"), (self.height, "720")):
            variable.set(value)
        self.show("捕获区域已恢复默认值。")

    def on_host_change(self, *_):
        password = saved_password(self.host.get().strip())
        self.password.set(password)
        self.remember.set(bool(password))

    def forget_password(self):
        host = self.host.get().strip()
        for target in (credential_target(host), legacy_credential_target(host)):
            try:
                win32cred.CredDelete(target, win32cred.CRED_TYPE_GENERIC, 0)
            except Exception:
                pass
        self.password.set("")
        self.remember.set(False)
        self.show("已删除当前地址的 Windows 凭据管理器密码。")

    def ask(self, title: str, question: str) -> bool:
        done = threading.Event()
        answer = {"yes": False}
        def prompt():
            answer["yes"] = messagebox.askyesno(title, question)
            done.set()
        self.root.after(0, prompt)
        done.wait()
        return answer["yes"]

    def task(self, fn):
        if self.busy:
            return
        self.busy = True
        def run():
            try:
                fn()
            except Exception as exc:
                self.show(f"操作未完成：{exc}")
                manager.log("gui_error", action=fn.__name__, error=str(exc)[:250])
            finally:
                self.busy = False
        threading.Thread(target=run, daemon=True).start()

    def connect(self):
        if self.client and self.client.get_transport() and self.client.get_transport().is_active():
            return self.client
        host = self.host.get().strip()
        if not re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", host):
            raise RuntimeError("请输入 RMPP 的 USB IPv4 地址")
        password = self.password.get()
        if not password:
            raise RuntimeError("请输入 root SSH 密码；本程序不保存密码")
        client = paramiko.SSHClient()
        if KNOWN_HOSTS.is_file():
            client.load_host_keys(str(KNOWN_HOSTS))
        else:
            KNOWN_HOSTS.parent.mkdir(parents=True, exist_ok=True)

        class FirstUsePin(paramiko.MissingHostKeyPolicy):
            def missing_host_key(self, ssh_client, hostname, key):
                ssh_client.get_host_keys().add(hostname, key.get_name(), key)
                ssh_client.save_host_keys(str(KNOWN_HOSTS))
                self_app.show(f"首次记录 RMPP SSH 主机密钥：{hostname} / {key.get_name()}。后续密钥变化会被拒绝。")

        self_app = self
        client.set_missing_host_key_policy(FirstUsePin())
        client.connect(host, username="root", password=password, look_for_keys=False,
                       allow_agent=False, timeout=7, auth_timeout=10)
        if self.remember.get():
            save_password(host, password)
        self.client = client
        return client

    def check(self):
        def work():
            state = manager.preflight(self.connect())
            self.show(f"检测格式 {state.get('probe_format', '旧版')}；RMPP {state['firmware']} / {state['arch']}；"
                      f"xochitl={state['xochitl']}；XOVI={state['xovi']}；安装记录={state['meta']}；"
                      f"VNSee PID={state.get('vnsee', '未读取') or '无'}；"
                      f"QMD 挂载={state.get('qmd_mount', '未读取')}；"
                      f"systemd 临时挂载={state.get('dropin_mount', '未读取')}；"
                      f"已加载 XOVI={state.get('loaded_xovi', '未读取') or '无'}；"
                      f"rmtool={state.get('rmtool', '未读取')}；停用标记={state.get('rmtool_disabled', '未读取')}；"
                      f"空闲 {state['free_kib']} KiB。")
        self.task(work)

    def backup_device(self):
        def work():
            if not self.ask("备份 RMPP", "请先在 RMPP 保存并关闭正在编辑的笔记。将只读备份笔记/PDF 文档库、用户配置、RMPP ScreenBridge/XOVI/AppLoad、rmtool 和 xochitl 启动配置到本机项目\"临时备份\\RMPP\"。不含系统分区或 SSH 私钥。备份通过完整性检查后才报告完成；继续吗？"):
                return
            path = manager.backup_device_data(self.connect(), "before-cleanup", self.show)
            self.show(f"RMPP 备份已验证，可用于后续清理前恢复参考：{path}")
        self.task(work)

    def install(self):
        def work():
            if not self.ask("安装离线文件", "将从官方地址在 Windows 下载并校验。写入设备前会先自动备份 RMPP 笔记、配置、rmtool 及相关软件到项目临时备份\\RMPP；备份失败会取消安装。不会启动 XOVI 或重启 xochitl。继续吗？"):
                return
            manager.install(self.connect(), self.show)
            self.show("离线文件已安装。新设备需要生成自己的 hashtab。")
            if self.ask("生成设备 hashtab", "请先保存 RMPP 未同步的笔记。系统会先把笔记、配置、rmtool 和相关软件备份到项目临时备份\\RMPP，再运行 XOVI 官方构建工具。该工具会暂停 xochitl，临时运行图形界面，可能要求在 RMPP 输入设备密码；结束后会恢复 stock。备份失败则取消。现在继续吗？"):
                manager.generate_hashtab(self.connect(), self.show)
                self.show("设备专用 hashtab 已生成并登记；现在可以连接投屏。")
        self.task(work)

    def complete(self):
        def work():
            try:
                manager.complete_hashtab(self.connect(), progress=self.show)
            except RuntimeError as exc:
                if "尚未生成设备 hashtab" not in str(exc):
                    raise
                if not self.ask("生成设备 hashtab", "请先保存未同步笔记。执行前会自动备份 RMPP 数据到项目临时备份\\RMPP，然后运行官方工具，临时中断并恢复 xochitl；设备可能要求输入密码。备份失败会取消。继续吗？"):
                    return
                manager.generate_hashtab(self.connect(), self.show)
            self.show("设备生成的 hashtab 已登记并核对，可进入启动检查。")
        self.task(work)

    def capture(self) -> tuple[int, int, int, int]:
        values = tuple(int(v.get()) for v in (self.x, self.y, self.width, self.height))
        x, y, w, h = values
        if x < 0 or y < 0 or w != 1620 or h != 720:
            raise RuntimeError("当前只验证了 1620×720；X、Y 必须非负，宽高不得更改")
        return values

    def ensure_forward(self, client):
        if self.forward:
            return
        owners = manager.remote(client, "cat /proc/net/tcp /proc/net/tcp6 | awk '$2 ~ /:170C$/ && $4 == \"0A\" {print $2}'")
        if owners.strip():
            raise RuntimeError("RMPP 5900 已被其他进程占用；未覆盖或终止它")
        transport = client.get_transport()
        transport.request_port_forward("127.0.0.1", 5900)
        self.forward = True
        def serve():
            while self.forward and transport.is_active():
                channel = transport.accept(timeout=1)
                if channel:
                    threading.Thread(target=pipe, args=(channel,), daemon=True).start()
        threading.Thread(target=serve, daemon=True).start()
        listeners = manager.remote(client, "cat /proc/net/tcp /proc/net/tcp6 | awk '$2 ~ /:170C$/ && $4 == \"0A\" {print $2}'").splitlines()
        if not listeners or any(value not in ("0100007F:170C", "00000000000000000000000001000000:170C") for value in listeners):
            self.forward = False
            transport.cancel_port_forward("127.0.0.1", 5900)
            raise RuntimeError("SSH 反向隧道未仅绑定 RMPP localhost")
        banner = manager.remote(client, "timeout 4 nc 127.0.0.1 5900 </dev/null | dd bs=1 count=12 2>/dev/null")
        if not banner.startswith("RFB 003.008"):
            self.forward = False
            transport.cancel_port_forward("127.0.0.1", 5900)
            raise RuntimeError("RMPP 侧未收到 Windows VNC 的 RFB 握手")

    def start(self):
        def work():
            x, y, w, h = self.capture()
            client = self.connect()
            active = manager.owned_active(client)
            receipt = manager.read_receipt(client) if active else manager.complete_hashtab(client, progress=self.show)
            manager.verify_tree(client, receipt)
            vnc_loopback()
            exe = tightvnc_exe()
            subprocess.run([str(exe), "-controlservice", "-sharerect", f"{w}x{h}+{x}+{y}"], timeout=15, check=False)
            if rfb_size() != (w, h):
                raise RuntimeError("TightVNC 实际 framebuffer 尺寸未变为 1620×720")
            self.ensure_forward(client)
            if not active:
                if not self.ask("启动 XOVI", "请保存 RMPP 尚未同步的笔记。执行前会自动备份到项目临时备份\\RMPP；随后临时启动 XOVI 并重启一次 xochitl。备份失败会取消。继续吗？"):
                    return
                manager.activate(client, self.show)
            self.show("已就绪：保持此窗口打开，在 RMPP AppLoad 选择 VNSee asivery Test。")
        self.task(work)

    def restore(self):
        def work():
            if not self.ask("恢复 stock", "请先正常退出 VNSee 并保存笔记。执行前会自动备份到项目临时备份\\RMPP，然后重启一次 xochitl。备份失败会取消。继续吗？"):
                return
            manager.restore_stock(self.connect(), self.show)
            self.show("stock 界面已恢复。")
        self.task(work)

    def uninstall(self):
        def work():
            if not self.ask("卸载", "请先在 AppLoad 正常退出 VNSee 并保存未同步笔记。每个恢复或删除步骤前都会自动备份到项目临时备份\\RMPP；若本项目 XOVI 正在运行，将恢复 stock 并重启 xochitl，然后按安装收据核对并移除文件。任一步备份失败都会取消该步。继续吗？"):
                return
            manager.uninstall(self.connect(), self.show)
            self.show("本安装器拥有的设备文件已卸载。")
        self.task(work)

    def close(self):
        if self.forward and not messagebox.askyesno("关闭隧道", "关闭窗口会断开 VNSee 的 VNC 隧道。继续吗？"):
            return
        self.forward = False
        if self.client:
            self.client.close()
        self.root.destroy()


if __name__ == "__main__":
    App().root.mainloop()
