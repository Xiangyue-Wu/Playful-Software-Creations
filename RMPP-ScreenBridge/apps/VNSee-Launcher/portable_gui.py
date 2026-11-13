"""Windows setup wizard for the supported RMPP profile.

Never stores a plaintext password or accepts an unknown SSH host key.
"""
from __future__ import annotations

import json
import base64
import os
import pathlib
import re
import socket
import subprocess
import threading
import urllib.request
import tkinter as tk
import winreg
from tkinter import messagebox, ttk

import paramiko
import win32api
import win32cred

import portable_manager as manager

HOST_DEFAULT = "10.11.99.1"
KNOWN_HOSTS = pathlib.Path.home() / ".ssh" / "known_hosts"
TIGHTVNC_URL = "https://www.tightvnc.com/download/2.8.90/tightvnc-2.8.90-gpl-setup-64bit.msi"
TIGHTVNC_SIZE = 2543616
TIGHTVNC_SHA256 = "9693cb4cdc2e7e482e8e3f5890415b57ef87de3369fa5c337db516218a1170ce"
TIGHTVNC_PRODUCT_CODE = "{AFF73242-938E-4D86-B133-6A287F7E4A04}"


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
        raise RuntimeError("没有安装 TightVNC Server 服务") from exc
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
    if version not in ((2, 8, 89), (2, 8, 90)):
        raise RuntimeError(f"仅支持 TightVNC Server 2.8.89/2.8.90；当前文件版本 {version}")
    return path


def tightvnc_settings() -> dict[str, int]:
    names = ("RfbPort", "AcceptRfbConnections", "AcceptHttpConnections",
             "AllowLoopback", "LoopbackOnly", "UseVncAuthentication")
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\TightVNC\Server", 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return {name: int(winreg.QueryValueEx(key, name)[0]) for name in names}
    except OSError as exc:
        raise RuntimeError("未找到完整的 TightVNC 服务安全配置；不会继续开放 VNC") from exc


def validate_tightvnc_settings(settings: dict[str, int]) -> None:
    expected = {"RfbPort": 5900, "AcceptRfbConnections": 1, "AcceptHttpConnections": 0,
                "AllowLoopback": 1, "LoopbackOnly": 1, "UseVncAuthentication": 0}
    wrong = [f"{name}={settings.get(name, '未设置')}（要求 {value}）"
             for name, value in expected.items() if settings.get(name) != value]
    if wrong:
        raise RuntimeError("TightVNC 当前设置不符合本项目的本机隧道要求：" + "; ".join(wrong) +
                           "。为避免覆盖已有设置，请先在 TightVNC 配置中调整")


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _powershell(script: str, timeout: int = 30) -> subprocess.CompletedProcess:
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    env = os.environ.copy()
    env["PSModulePath"] = (r"C:\Windows\System32\WindowsPowerShell\v1.0\Modules;"
                           r"C:\Program Files\WindowsPowerShell\Modules")
    return subprocess.run(["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
                           "-EncodedCommand", encoded], env=env,
                          capture_output=True, text=True, timeout=timeout)


def download_tightvnc(progress) -> pathlib.Path:
    path = manager.CACHE / pathlib.PurePosixPath(TIGHTVNC_URL).name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.stat().st_size != TIGHTVNC_SIZE or manager.file_sha(path) != TIGHTVNC_SHA256:
            raise RuntimeError(f"已有 {path.name} 校验不符；保留文件供检查")
    else:
        part = path.with_name(path.name + ".part")
        if part.exists():
            raise RuntimeError(f"存在未完成的 TightVNC 下载：{part}；请先检查")
        progress("正在从 TightVNC 官方站点下载已签名的 Server 安装包…")
        try:
            request = urllib.request.Request(TIGHTVNC_URL, headers={"User-Agent": "RMPP-ScreenBridge/0.1"})
            with urllib.request.urlopen(request, timeout=45) as response, part.open("xb") as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
            if part.stat().st_size != TIGHTVNC_SIZE or manager.file_sha(part) != TIGHTVNC_SHA256:
                raise RuntimeError("TightVNC MSI 大小或 SHA256 校验失败")
            part.replace(path)
            manager.log("download_verified", name="tightvnc", sha256=TIGHTVNC_SHA256,
                        size=TIGHTVNC_SIZE, url=TIGHTVNC_URL)
        except Exception:
            part.unlink(missing_ok=True)
            raise

    signature_check = (
        f"Import-Module Microsoft.PowerShell.Security -ErrorAction Stop; "
        f"$s=Get-AuthenticodeSignature -LiteralPath {_ps_quote(str(path))}; "
        "if ($s.Status -ne 'Valid' -or $s.SignerCertificate.Subject -notmatch 'CN=OOO GlavSoft') { exit 41 }"
    )
    result = _powershell(signature_check)
    if result.returncode != 0:
        raise RuntimeError("TightVNC 安装包的 Authenticode 签名无效或签名者不符")
    return path


def install_tightvnc(msi: pathlib.Path, progress) -> None:
    log_path = manager.PROJECT / "logs" / "tightvnc-install.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    arguments = (
        f'/i "{msi}" /qn /norestart /l*v "{log_path}" '
        'ADDLOCAL=Server SERVER_REGISTER_AS_SERVICE=1 SERVER_ADD_FIREWALL_EXCEPTION=0 '
        'SET_RFBPORT=1 VALUE_OF_RFBPORT=5900 '
        'SET_ACCEPTHTTPCONNECTIONS=1 VALUE_OF_ACCEPTHTTPCONNECTIONS=0 '
        'SET_ALLOWLOOPBACK=1 VALUE_OF_ALLOWLOOPBACK=1 '
        'SET_LOOPBACKONLY=1 VALUE_OF_LOOPBACKONLY=1 '
        'SET_USEVNCAUTHENTICATION=1 VALUE_OF_USEVNCAUTHENTICATION=0'
    )
    script = (f"$p=Start-Process -FilePath 'msiexec.exe' -ArgumentList {_ps_quote(arguments)} "
              "-Verb RunAs -Wait -PassThru; exit $p.ExitCode")
    progress("Windows 将弹出 UAC 确认；只安装 TightVNC Server，关闭防火墙例外、Web 访问和 VNC 密码认证，并限制为 loopback 连接…")
    result = _powershell(script, timeout=600)
    manager.log("tightvnc_msi_exit", exit_code=result.returncode)
    if result.returncode != 0:
        raise RuntimeError(f"TightVNC 安装未完成（退出码 {result.returncode}）；设备端 XOVI 尚未启动")


def tightvnc_service_state() -> tuple[str, int]:
    script = ("$s=Get-CimInstance Win32_Service -Filter \"Name='tvnserver'\"; "
              "if(-not $s){exit 2}; Write-Output ($s.State + ':' + $s.ProcessId)")
    result = _powershell(script)
    if result.returncode != 0:
        return "Absent", 0
    state, pid = result.stdout.strip().split(":", 1)
    return state, int(pid)


def tightvnc_product() -> dict:
    script = r"""
$keys=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*')
$items=Get-ItemProperty $keys -ErrorAction SilentlyContinue |
  Where-Object { $_.DisplayName -match '^TightVNC( Server)?$' -and $_.DisplayVersion -like '2.8.90*' }
if(@($items).Count -ne 1){exit 3}
$item=@($items)[0]
@{ProductCode=(Split-Path $item.PSPath -Leaf);DisplayName=$item.DisplayName;Version=$item.DisplayVersion} |
  ConvertTo-Json -Compress
"""
    result = _powershell(script)
    if result.returncode != 0:
        raise RuntimeError("无法唯一核对 TightVNC 2.8.90 的 Windows 安装记录")
    return json.loads(result.stdout.strip())


def tightvnc_install_records() -> list[dict]:
    script = r"""
$keys=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*')
$items=@(Get-ItemProperty $keys -ErrorAction SilentlyContinue |
  Where-Object { $_.DisplayName -match '^TightVNC' } |
  ForEach-Object { @{ProductCode=(Split-Path $_.PSPath -Leaf);DisplayName=[string]$_.DisplayName;Version=[string]$_.DisplayVersion} })
ConvertTo-Json -InputObject $items -Compress -Depth 3
"""
    result = _powershell(script)
    if result.returncode != 0:
        raise RuntimeError("Windows 无法读取 TightVNC 安装记录；未修改现有程序")
    out = result.stdout.strip()
    if not out:
        return []
    items = json.loads(out)
    return items if isinstance(items, list) else [items]


def record_tightvnc_install(exe: pathlib.Path, preexisting_product: bool) -> pathlib.Path:
    product = tightvnc_product()
    if not re.fullmatch(r"\{?[0-9a-fA-F-]{36}\}?", product.get("ProductCode", "")):
        raise RuntimeError("TightVNC 安装记录没有有效产品代码；无法建立安全卸载收据")
    if product["ProductCode"].upper() != TIGHTVNC_PRODUCT_CODE:
        raise RuntimeError("TightVNC 产品代码与本项目校验过的官方 MSI 不符；停止并保留已安装程序")
    receipt = {
        "format": 1,
        "owner": "RMPP-ScreenBridge",
        "product_code": product["ProductCode"],
        "display_name": product["DisplayName"],
        "version": product["Version"],
        "preexisting_product": bool(preexisting_product),
        "service_exe": str(exe.resolve()),
        "service_exe_sha256": manager.file_sha(exe),
        "msi_sha256": TIGHTVNC_SHA256,
    }
    path = manager.PROJECT / "config" / "tightvnc-install-receipt.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if (existing.get("format") != 1 or existing.get("owner") != "RMPP-ScreenBridge"
                or existing.get("product_code") != receipt["product_code"]
                or existing.get("service_exe") != receipt["service_exe"]
                or existing.get("service_exe_sha256") != receipt["service_exe_sha256"]
                or existing.get("msi_sha256") != TIGHTVNC_SHA256):
            raise RuntimeError("已有 TightVNC 安装收据与当前安装不符；保留现状，不覆盖")
        # Preserve whether this project created the product originally. A repair
        # must not turn a previously owned install into a pre-existing one.
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manager.log("tightvnc_install_receipt_created", product_code=product["ProductCode"],
                version=product["Version"], service_exe_sha256=receipt["service_exe_sha256"])
    return path


def start_tightvnc_service() -> None:
    result = _powershell("$p=Start-Process -FilePath 'sc.exe' -ArgumentList 'start tvnserver' "
                         "-Verb RunAs -Wait -PassThru; exit $p.ExitCode", timeout=90)
    if result.returncode != 0:
        raise RuntimeError("TightVNC 服务未能启动；未启动 XOVI")


def set_tightvnc_capture(exe: pathlib.Path, rect: str) -> None:
    argument_list = f'-controlservice -sharerect "{rect}"'
    script = (f"$p=Start-Process -FilePath {_ps_quote(str(exe))} "
              f"-ArgumentList {_ps_quote(argument_list)} -Verb RunAs -Wait -PassThru; exit $p.ExitCode")
    result = _powershell(script, timeout=45)
    manager.log("tightvnc_capture_requested", rect=rect, exit_code=result.returncode)
    if result.returncode != 0:
        raise RuntimeError("Windows UAC 未批准或 TightVNC 捕获区域命令失败；RMPP XOVI 尚未启动")


def ensure_tightvnc(ask, progress) -> pathlib.Path:
    try:
        exe = tightvnc_exe()
        validate_tightvnc_settings(tightvnc_settings())
    except RuntimeError as exc:
        if "没有安装 TightVNC Server 服务" not in str(exc):
            raise
        # Do not install over a stray application-mode server or an unknown listener.
        probe = _powershell("$p=Get-NetTCPConnection -LocalPort 5900 -State Listen -ErrorAction SilentlyContinue; "
                            "if($p){exit 2}; exit 0")
        if probe.returncode != 0:
            raise RuntimeError("5900 端口已有未识别监听；为避免覆盖其他 VNC 实例，停止安装")
        records = tightvnc_install_records()
        msi = download_tightvnc(progress)
        prior = "；检测到现有登记：" + "、".join(
            f"{row.get('DisplayName', 'TightVNC')} {row.get('Version', '版本未知')} [{row.get('ProductCode', '代码未知')}]"
            for row in records) if records else ""
        prompt = ("将通过 Windows UAC 使用官方 TightVNC 2.8.90 MSI 安装/修复 Server-only。"
                  "服务端口为 5900，启用 loopback-only、关闭 Web 访问和 VNC 密码认证、不添加防火墙例外。"
                  "若电脑已有 TightVNC，安装器可能执行同系列升级；不会主动删除已有文件。" + prior + "。继续吗？")
        if not ask("安装或修复 TightVNC Server", prompt):
            raise RuntimeError("你取消了 TightVNC 安装；RMPP XOVI 尚未启动")
        install_tightvnc(msi, progress)
        exe = tightvnc_exe()
        receipt = record_tightvnc_install(exe, preexisting_product=bool(records))
        progress(f"TightVNC 已按项目配置安装；本机卸载收据：{receipt}")
        validate_tightvnc_settings(tightvnc_settings())

    state, pid = tightvnc_service_state()
    if state != "Running":
        if not ask("启动 TightVNC Server", "TightVNC 服务已安装并通过本机访问配置检查。现在启动服务以继续投屏吗？"):
            raise RuntimeError("你取消了 TightVNC 服务启动；RMPP XOVI 尚未启动")
        start_tightvnc_service()
        state, pid = tightvnc_service_state()
    if state != "Running" or pid <= 0:
        raise RuntimeError("TightVNC Server 服务仍未运行；RMPP XOVI 尚未启动")
    return exe


def uninstall_tightvnc_if_owned(progress=lambda text: None) -> str:
    path = manager.PROJECT / "config" / "tightvnc-install-receipt.json"
    if not path.is_file():
        return "没有本项目 TightVNC 安装收据；未卸载任何 TightVNC。"
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt.get("format") != 1 or receipt.get("owner") != "RMPP-ScreenBridge":
            raise RuntimeError("收据格式或归属不匹配")
        exe = pathlib.Path(receipt["service_exe"])
        if not exe.is_file() or manager.file_sha(exe) != receipt.get("service_exe_sha256"):
            raise RuntimeError("服务文件路径或 SHA256 与安装收据不符")
        product = tightvnc_product()
        if (product.get("ProductCode") != receipt.get("product_code")
                or product.get("Version") != receipt.get("version")):
            raise RuntimeError("Windows 安装产品与收据不符")
        service_exe = tightvnc_exe()
        if service_exe.resolve() != exe.resolve():
            raise RuntimeError("当前 TightVNC 服务路径与安装收据不符")
    except Exception as exc:
        return f"TightVNC 保留：无法证明它由本项目安装（{exc}）。"
    preexisting = bool(receipt.get("preexisting_product", False))
    if preexisting:
        msi = manager.CACHE / pathlib.PurePosixPath(TIGHTVNC_URL).name
        if (not msi.is_file() or msi.stat().st_size != TIGHTVNC_SIZE
                or manager.file_sha(msi) != TIGHTVNC_SHA256):
            return "TightVNC 保留：原安装记录仍在，但验证过的 MSI 缓存不存在，无法安全只移除本项目加入的 Server 功能。"
        progress("将通过 Windows UAC 移除本项目加入的 TightVNC Server 功能，保留此前已存在的 TightVNC 产品/Viewer；这会断开投屏。")
    else:
        progress("将通过 Windows UAC 卸载收据匹配的本项目 TightVNC 2.8.90；这会停止 VNC 服务并断开投屏。")
    code = receipt["product_code"]
    if preexisting:
        msi_arg = str(msi)
        args = f'/i "{msi_arg}" /qn /norestart REMOVE=Server'
    else:
        args = f'/x {code} /qn /norestart'
    script = (f"$p=Start-Process -FilePath 'msiexec.exe' -ArgumentList "
              f"{_ps_quote(args)} -Verb RunAs -Wait -PassThru; exit $p.ExitCode")
    result = _powershell(script, timeout=600)
    if result.returncode != 0:
        return f"TightVNC 卸载未完成（退出码 {result.returncode}）；收据和文件保留。"
    state, _pid = tightvnc_service_state()
    if state != "Absent":
        return "TightVNC MSI 已运行，但 Server 服务仍存在；保留收据供检查。"
    path.unlink()
    return "已按匹配的本项目收据卸载 TightVNC 2.8.90。"


def vnc_loopback() -> None:
    validate_tightvnc_settings(tightvnc_settings())
    query = ("$p=@(Get-NetTCPConnection -LocalPort 5900 -State Listen -ErrorAction SilentlyContinue | "
             "Select-Object LocalAddress,OwningProcess); "
             "$s=Get-CimInstance Win32_Service -Filter \"Name='tvnserver'\"; "
             "@{Listeners=$p;ServicePid=[int]$s.ProcessId;State=$s.State} | ConvertTo-Json -Compress -Depth 4")
    result = _powershell(query, timeout=15)
    if result.returncode != 0:
        raise RuntimeError("无法读取 TightVNC 监听状态")
    out = result.stdout.strip()
    state = json.loads(out) if out else {}
    rows = state.get("Listeners") or []
    if isinstance(rows, dict):
        rows = [rows]
    if state.get("State") != "Running" or not rows:
        raise RuntimeError("TightVNC 服务没有在 Windows 5900 端口监听")
    if any(int(row["OwningProcess"]) != int(state.get("ServicePid", -1)) for row in rows):
        raise RuntimeError("Windows 5900 监听者不是已核验的 TightVNC 服务；拒绝复用")
    allowed = {"127.0.0.1", "::1", "0.0.0.0", "::"}
    if any(row["LocalAddress"] not in allowed for row in rows):
        raise RuntimeError("TightVNC 监听地址异常；拒绝继续")


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
            (3, "一键准备并开始投屏", self.start),
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
            if active:
                receipt = manager.read_receipt(client)
            else:
                state = manager.preflight(client)
                if state["xovi"] == "absent" and state["meta"] == "absent":
                    if not self.ask("安装 RMPP 组件", "尚未安装 ScreenBridge 管理的 XOVI/AppLoad/VNSee。继续后会下载官方文件、先备份 RMPP 笔记与 rmtool 状态，再通过 USB SSH 离线安装；不会立即启动 XOVI。继续吗？"):
                        return
                    manager.install(client, self.show)
                    state = manager.preflight(client)
                if state["xovi"] != "present" or state["meta"] != "present":
                    raise RuntimeError("RMPP 组件状态不完整；未覆盖文件，停止一键流程")
                receipt = manager.read_receipt(client)
                if not receipt.get("hashtab_sha256"):
                    if not self.ask("生成设备 hashtab", "新设备需要为当前固件生成一次 hashtab。请先保存未同步笔记；操作前会备份笔记、配置和 rmtool，然后运行 XOVI 官方工具并恢复 stock 界面。继续吗？"):
                        return
                    manager.generate_hashtab(client, self.show)
                    receipt = manager.complete_hashtab(client, progress=self.show)
            manager.verify_tree(client, receipt)
            exe = ensure_tightvnc(self.ask, self.show)
            vnc_loopback()
            set_tightvnc_capture(exe, f"{w}x{h}+{x}+{y}")
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
