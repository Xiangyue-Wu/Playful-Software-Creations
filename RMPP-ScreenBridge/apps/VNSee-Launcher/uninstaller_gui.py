"""Standalone, receipt-based uninstaller for RMPP ScreenBridge."""
from __future__ import annotations

import base64
import json
import os
import pathlib
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import paramiko
import win32cred

import portable_manager as manager

HOST_DEFAULT = "10.11.99.1"
KNOWN_HOSTS = pathlib.Path.home() / ".ssh" / "known_hosts"
CREDENTIAL_TARGETS = ("RMPP-ScreenBridge:ssh:root@", "RMPP-VNSee-Portable:ssh:root@")


def saved_password(host: str) -> str:
    for prefix in CREDENTIAL_TARGETS:
        try:
            blob = win32cred.CredRead(prefix + host, win32cred.CRED_TYPE_GENERIC, 0)["CredentialBlob"]
            return blob.decode("utf-16-le") if isinstance(blob, bytes) else blob
        except Exception:
            pass
    return ""


class FirstUsePin(paramiko.MissingHostKeyPolicy):
    """Trust-on-first-use, then persist and require the same host key."""
    def missing_host_key(self, client, hostname, key):
        client.get_host_keys().add(hostname, key.get_name(), key)
        client.save_host_keys(str(KNOWN_HOSTS))


class Uninstaller:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("RMPP ScreenBridge 卸载器")
        self.root.geometry("670x565")
        self.root.minsize(610, 500)
        self.host = tk.StringVar(value=HOST_DEFAULT)
        self.password = tk.StringVar(value=saved_password(HOST_DEFAULT))
        self.clean_windows = tk.BooleanVar(value=True)
        self.remove_venv = tk.BooleanVar(value=True)
        self.remove_owned_tightvnc = tk.BooleanVar(value=True)
        self.busy = False

        body = ttk.Frame(self.root, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="RMPP ScreenBridge 卸载器", font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(body, text=("设备端会先按本项目收据核验所有权；若本项目 XOVI 正在运行，会恢复 stock。"
                              "USB/SSH 不可用时，设备端不会被宣称为已卸载。"),
                  wraplength=620).pack(anchor="w", pady=(7, 12))

        form = ttk.Frame(body)
        form.pack(fill="x")
        ttk.Label(form, text="RMPP USB IP").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.host, width=38).grid(row=0, column=1, sticky="ew", padx=10)
        ttk.Label(form, text="root SSH 密码").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.password, show="*", width=38).grid(row=1, column=1, sticky="ew", padx=10)
        form.columnconfigure(1, weight=1)

        local = ttk.LabelFrame(body, text="Windows 本地项目数据", padding=9)
        local.pack(fill="x", pady=11)
        ttk.Checkbutton(local, text="清理经哈希确认的项目下载、离线安装包和项目日志",
                        variable=self.clean_windows).pack(anchor="w")
        ttk.Checkbutton(local, text="同时删除本项目 .venv（不会卸载系统 Python）",
                        variable=self.remove_venv).pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(local, text="卸载本项目自动安装的 TightVNC（仅收据、版本、路径、哈希全部匹配时）",
                        variable=self.remove_owned_tightvnc).pack(anchor="w", pady=(4, 0))

        buttons = ttk.Frame(body)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="卸载 RMPP + 清理所选 Windows 文件",
                   command=self.uninstall_all).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(buttons, text="只清理 Windows 文件",
                   command=self.uninstall_local).pack(side="left", expand=True, fill="x", padx=(5, 0))
        ttk.Button(body, text="卸载设备并彻底删除本项目目录（含本地备份）",
                   command=self.uninstall_everything).pack(fill="x", pady=(5, 0))

        ttk.Label(body, text="状态与结果（可选中复制）").pack(anchor="w", pady=(11, 3))
        self.output = tk.Text(body, height=13, wrap="word")
        self.output.pack(fill="both", expand=True)
        self.say("普通清理会保留源码和卸载器；“彻底删除”需另行确认，会删除本解压目录内的本地备份。RMPP 笔记、rmtool 和其他 SSH 主机密钥不会被删除。")

    def say(self, text: str):
        def append():
            self.output.insert("end", text + "\n")
            self.output.see("end")
        self.root.after(0, append)

    def ask(self, title: str, text: str) -> bool:
        done = threading.Event()
        result = {"yes": False}
        def prompt():
            result["yes"] = messagebox.askyesno(title, text, parent=self.root)
            done.set()
        self.root.after(0, prompt)
        done.wait()
        return result["yes"]

    def run_worker(self, action):
        if self.busy:
            return
        self.busy = True
        def worker():
            try:
                action()
            except Exception as exc:
                self.say(f"未完成：{exc}")
                manager.log("standalone_uninstall_error", error=str(exc)[:300])
            finally:
                self.busy = False
        threading.Thread(target=worker, daemon=True).start()

    def connect(self):
        return self.connect_to(self.host.get().strip(), self.password.get())

    @staticmethod
    def connect_to(host: str, password: str):
        if not host or any(c in host for c in "\r\n\x00"):
            raise RuntimeError("请输入有效的 RMPP USB 地址")
        if not password:
            raise RuntimeError("请输入 root SSH 密码；密码不会写入卸载日志")
        client = paramiko.SSHClient()
        if KNOWN_HOSTS.is_file():
            client.load_host_keys(str(KNOWN_HOSTS))
        else:
            KNOWN_HOSTS.parent.mkdir(parents=True, exist_ok=True)
        client.set_missing_host_key_policy(FirstUsePin())
        client.connect(host, username="root", password=password, look_for_keys=False,
                       allow_agent=False, timeout=7, auth_timeout=10)
        return client

    def uninstall_all(self):
        if not messagebox.askyesno(
                "卸载 RMPP ScreenBridge",
                "设备端每个恢复/删除步骤前会先备份 RMPP 数据到项目临时备份\\RMPP，可能恢复 stock 并重启 xochitl；"
                "Windows 部分可按收据卸载本程序自动安装的 TightVNC 2.8.90（会停止 VNC 服务并断开投屏）；"
                "不会卸载你原先安装的 TightVNC。请先在 RMPP 正常退出 VNSee 并保存未同步笔记。"
                "卸载仅处理本项目收据逐项列出的文件。继续吗？",
                parent=self.root):
            return
        host, password = self.host.get().strip(), self.password.get()
        clean_windows, remove_venv = self.clean_windows.get(), self.remove_venv.get()
        remove_tightvnc = self.remove_owned_tightvnc.get()
        def work():
            client = None
            device_done = False
            try:
                self.say("连接 RMPP 并核对本项目安装收据…")
                client = self.connect_to(host, password)
                active = manager.owned_active(client)
                if active:
                    self.say("发现本项目临时 XOVI 正在运行，按收据恢复 stock…")
                    manager.restore_stock(client, self.say)
                manager.uninstall(client, self.say)
                device_done = True
                self.say("RMPP：本项目设备文件已按收据核验并卸载；stock 状态已检查。")
            except Exception as exc:
                self.say(f"RMPP：卸载未完成，设备文件保留以便安全重试。原因：{exc}")
                manager.log("standalone_device_uninstall_incomplete", error=str(exc)[:300])
            finally:
                if client:
                    client.close()
            if clean_windows:
                removed, kept = self.cleanup_windows(host, remove_venv, remove_tightvnc)
                self.say("Windows：已清理 " + (", ".join(removed) if removed else "无匹配的项目缓存文件") + ".")
                if kept:
                    self.say("Windows：以下项目文件因哈希/收据不符而保留：" + ", ".join(kept))
            if not device_done:
                self.say("最终状态：仅完成所选 Windows 本地清理；RMPP 端需要 USB/SSH 恢复后重试。")
        self.run_worker(work)

    def uninstall_local(self):
        if not messagebox.askyesno(
                "只清理 Windows 项目文件",
                "将清理本项目能按固定哈希或安装收据确认的下载、安装包、日志和凭据；"
                "如勾选且本项目安装收据完全匹配，还会通过 UAC 卸载本程序自动安装的 TightVNC。"
                "不会连接或修改 RMPP。源码及卸载器保留。继续吗？",
                parent=self.root):
            return
        host, remove_venv = self.host.get().strip(), self.remove_venv.get()
        remove_tightvnc = self.remove_owned_tightvnc.get()
        def work():
            removed, kept = self.cleanup_windows(host, remove_venv, remove_tightvnc)
            self.say("Windows 本地清理完成：" + (", ".join(removed) if removed else "没有可安全识别的缓存文件") + ".")
            if kept:
                self.say("未删除（哈希或收据不符）：" + ", ".join(kept))
        self.run_worker(work)

    def uninstall_everything(self):
        raw_project = manager.PROJECT
        project = raw_project.resolve()
        required = ("BUILD-INFO.txt", "RMPP-ScreenBridge.exe", "启动安装器.cmd", "卸载RMPP-ScreenBridge.cmd")
        allowed = set(required) | {"README.md", "README.zh-CN.md", "LICENSE", "THIRD_PARTY.md",
                                   "docs", "deploy", "downloads", "config", "logs", "临时备份", ".venv"}
        if raw_project.is_symlink() or raw_project != project or any(not (project / name).is_file() for name in required):
            self.say("拒绝彻底删除：当前不是完整的 Release 解压目录；源码和未知目录会保留。")
            return
        unknown = sorted(p.name for p in project.iterdir() if p.name not in allowed)
        if unknown:
            self.say("拒绝彻底删除：目录内有未识别的文件/目录：" + ", ".join(unknown))
            return
        if any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()) for p in project.rglob("*")):
            self.say("拒绝彻底删除：项目目录内存在符号链接或联接点。")
            return
        prompt = (f"即将按安装收据卸载 RMPP 设备文件和本项目安装的 Windows TightVNC Server，"
                  f"再删除整个目录及其中的笔记/PDF 备份：\n{project}\n\n"
                  "请先保存 RMPP 笔记、正常退出 VNSee，并关闭投屏主窗口。"
                  "设备卸载失败时会保留目录，以便重试。确定继续吗？")
        if not messagebox.askyesno("彻底卸载 RMPP ScreenBridge", prompt, parent=self.root):
            return
        host, password = self.host.get().strip(), self.password.get()

        def work():
            client = None
            try:
                client = self.connect_to(host, password)
                manager.uninstall(client, self.say)
                self.say("RMPP 设备文件卸载完成；正在核对 Windows 清理结果…")
            finally:
                if client:
                    client.close()
            removed, kept = self.cleanup_windows(host, False, True)
            if kept or (project / "config" / "tightvnc-install-receipt.json").exists():
                self.say("Windows 清理尚有未完成项目，整个目录已保留：" + ", ".join(kept))
                return
            self.say("已清理：" + (", ".join(removed) if removed else "无额外缓存"))
            quoted = "'" + str(project).replace("'", "''") + "'"
            script = (f"$target={quoted}; $expected={quoted}; "
                      "if ([IO.Path]::GetFullPath($target) -ne $expected -or "
                      "((Get-Item -LiteralPath $target).Attributes -band [IO.FileAttributes]::ReparsePoint) -or "
                      "-not (Test-Path -LiteralPath (Join-Path $target 'BUILD-INFO.txt')) -or "
                      "-not (Test-Path -LiteralPath (Join-Path $target '卸载RMPP-ScreenBridge.cmd'))) {exit 2}; "
                      f"Wait-Process -Id {os.getpid()} -Timeout 180 -ErrorAction SilentlyContinue; "
                      "Start-Sleep -Seconds 2; "
                      "for($i=0;$i -lt 10;$i++){try{Remove-Item -LiteralPath $target -Recurse -Force "
                      "-ErrorAction Stop; exit 0}catch{Start-Sleep -Seconds 2}}; exit 3")
            encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
            subprocess.Popen(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                             creationflags=0x08000000, close_fds=True)
            def finish():
                messagebox.showinfo("卸载完成", "设备文件已卸载。本窗口关闭后将删除整个项目目录及其中的临时备份。", parent=self.root)
                self.root.destroy()
            self.root.after(0, finish)

        self.run_worker(work)

    def cleanup_windows(self, host: str, remove_venv: bool, remove_tightvnc: bool = False) -> tuple[list[str], list[str]]:
        project = manager.PROJECT
        removed: list[str] = []
        kept: list[str] = []
        if remove_tightvnc:
            try:
                from portable_gui import uninstall_tightvnc_if_owned
                result = uninstall_tightvnc_if_owned(self.say)
                if result.startswith("已按"):
                    removed.append(result)
                elif not result.startswith("没有本项目"):
                    kept.append(result)
            except Exception as exc:
                kept.append(f"TightVNC 保留（卸载检查失败：{exc}）")
        cache = project / "downloads"
        for name, (url, size, digest) in manager.SOURCES.items():
            path = cache / pathlib.PurePosixPath(url).name
            if not path.exists():
                pass
            elif path.is_file() and path.stat().st_size == size and manager.file_sha(path) == digest:
                path.unlink()
                removed.append(str(path.relative_to(project)))
            else:
                kept.append(str(path.relative_to(project)) + "（大小或哈希不同）")
            partial = path.with_name(path.name + ".part")
            if partial.is_file():
                partial.unlink()
                removed.append(str(partial.relative_to(project)))

        bundle_dir = project / "deploy" / "portable-bundles"
        receipt_path = bundle_dir / "install-receipt.json"
        bundle_path = bundle_dir / "xovi-appload-vnsee.tar.gz"
        if receipt_path.is_file() or bundle_path.is_file():
            try:
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                if (receipt.get("owner") == "RMPP-VNSee-Portable" and bundle_path.is_file()
                        and manager.file_sha(bundle_path) == receipt.get("bundle_sha256")):
                    bundle_path.unlink()
                    receipt_path.unlink()
                    removed.extend([str(bundle_path.relative_to(project)), str(receipt_path.relative_to(project))])
                else:
                    kept.append("deploy/portable-bundles（包或本项目收据不匹配）")
            except Exception:
                kept.append("deploy/portable-bundles（收据无法验证）")

        log_path = manager.LOG
        if log_path.is_file():
            log_path.unlink()
            removed.append(str(log_path.relative_to(project)))

        tightvnc_msi = project / "downloads" / "tightvnc-2.8.90-gpl-setup-64bit.msi"
        if tightvnc_msi.is_file():
            from portable_gui import TIGHTVNC_SHA256, TIGHTVNC_SIZE
            tightvnc_receipt = project / "config" / "tightvnc-install-receipt.json"
            if tightvnc_receipt.exists():
                kept.append("downloads/tightvnc-2.8.90-gpl-setup-64bit.msi（TightVNC 收据仍在，保留以便安全重试卸载）")
            elif tightvnc_msi.stat().st_size == TIGHTVNC_SIZE and manager.file_sha(tightvnc_msi) == TIGHTVNC_SHA256:
                tightvnc_msi.unlink()
                removed.append(str(tightvnc_msi.relative_to(project)))
            else:
                kept.append(str(tightvnc_msi.relative_to(project)) + "（大小或哈希不同）")

        if remove_venv:
            venv = project / ".venv"
            if venv.is_dir() and (venv / "pyvenv.cfg").is_file():
                quoted = str(venv).replace("'", "''")
                wait_and_remove = (f"Wait-Process -Id {os.getpid()}; "
                                   f"if (Test-Path -LiteralPath '{quoted}') "
                                   f"{{ Remove-Item -LiteralPath '{quoted}' -Recurse -Force }}")
                subprocess.Popen(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", wait_and_remove],
                                 creationflags=0x08000000, close_fds=True)
                removed.append(".venv（卸载器退出后删除）")

        for directory in (cache, project / "logs", bundle_dir):
            try:
                directory.rmdir()
            except OSError:
                pass

        for prefix in CREDENTIAL_TARGETS:
            try:
                win32cred.CredDelete(prefix + host, win32cred.CRED_TYPE_GENERIC, 0)
                removed.append("本项目 root SSH 凭据")
            except Exception:
                pass
        # known_hosts is shared with OpenSSH/other projects; intentionally leave it untouched.
        return removed, kept


if __name__ == "__main__":
    Uninstaller().root.mainloop()
