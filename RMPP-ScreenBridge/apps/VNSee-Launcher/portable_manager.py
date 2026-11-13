"""Portable, fail-closed installer for one tested RMPP firmware profile.

Downloads are made on Windows. No package manager or network access is used on
the tablet. The installer never modifies systemd, rmtool, or user documents.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import pathlib
import re
import shlex
import shutil
import sys
import tarfile
import time
import urllib.request
import uuid
import zlib

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

PROJECT = (pathlib.Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
           else pathlib.Path(__file__).resolve().parents[2])
CACHE = PROJECT / "downloads"
LOG = PROJECT / "logs" / "portable-installer.jsonl"
ROOT = "/home/root/xovi"
META = "/home/root/.vnsee-portable"
FIRMWARE = "3.29.0.153"
KEY_SHA256 = "2cf3d32486a5b231170586475221fc222887ccb8a3b9345b577a88d2908bc847"
ELF_SHA256 = "204afcfde8a2cc4139c618aaade8b13d9034e14b00477ff984193cf4e1d3214f"
SOURCES = {
    "xovi": ("https://github.com/asivery/rm-xovi-extensions/releases/download/v19-23052026/xovi-aarch64.tar.gz", 6163890,
             "32d64d1262ddc984e3235c7d0340a398fe6d5b3efa6a979865f5977b32630d27"),
    "appload": ("https://github.com/asivery/rm-appload/releases/download/v0.6.0/appload-aarch64.tar.gz", 4405410,
                "2e7912d15df910631dab847ea5d344081ad75c02a46aaac78bdf731accc53a1f"),
    "vnsee": ("https://packages.vellum.delivery/aarch64/vnsee-qtfb-1.1.1-r0.apk", 262125,
              "24575e0ac2c81f791677d8b648432fa8bcedcb10239179d4837ef34c9441cd41"),
    "vellum_key": ("https://raw.githubusercontent.com/vellum-dev/vellum/main/keys/packages.rsa.pub", 800, KEY_SHA256),
}
BACKUP_ROOT = PROJECT / "临时备份" / "RMPP"
BACKUP_PATHS = (
    "/home/root/.local/share/remarkable/xochitl",
    "/home/root/.config",
    "/home/root/xovi",
    "/home/root/.vnsee-portable",
    "/data/rmtool",
    "/etc/systemd/system/xochitl.service",
    "/etc/systemd/system/xochitl.service.d",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def log(event: str, **fields) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as out:
        out.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event, **fields},
                             ensure_ascii=False, sort_keys=True) + "\n")


def backup_device_data(client, operation: str, progress=lambda text: None) -> pathlib.Path:
    """Stream a scoped, read-only RMPP data/config snapshot to Windows.

    No archive is written to the tablet. The snapshot excludes OS partitions,
    SSH private keys, and unsaved in-memory note edits; callers must obtain
    note-save consent before operations that restart xochitl.
    """
    if not re.fullmatch(r"[a-z0-9-]{1,32}", operation):
        raise RuntimeError("备份操作名称无效")
    progress("正在把 RMPP 笔记/文档、项目配置及 rmtool 状态备份到 Windows…")
    quoted = " ".join(shlex.quote(path) for path in BACKUP_PATHS)
    exists = remote(client, "for p in " + quoted + "; do if [ -e \"$p\" ] || [ -L \"$p\" ]; then printf '%s\\n' \"$p\"; fi; done").splitlines()
    notes_root = "/home/root/.local/share/remarkable/xochitl"
    if notes_root not in exists or remote(client, f"test -d {shlex.quote(notes_root)} && test ! -L {shlex.quote(notes_root)} && echo ok || echo invalid").strip() != "ok":
        raise RuntimeError("未找到预期的 RMPP 笔记数据库目录；为避免生成不完整备份，已取消风险操作")
    if remote(client, f"find {shlex.quote(notes_root)} -type l -print -quit").strip():
        raise RuntimeError("笔记数据库内存在符号链接；当前备份器不会跟随链接，已取消以免遗漏 PDF/笔记")
    paths = [path for path in BACKUP_PATHS if path in exists]
    size_text = remote(client, "du -sk " + " ".join(shlex.quote(path) for path in paths))
    estimated_kib = sum(int(line.split()[0]) for line in size_text.splitlines() if line.strip())
    free_bytes = shutil.disk_usage(PROJECT).free
    if free_bytes < estimated_kib * 1024 + 64 * 1024 * 1024:
        raise RuntimeError(f"项目磁盘空间不足以安全备份（估算 {estimated_kib} KiB）；未执行风险操作")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    project_root = PROJECT.resolve()
    if BACKUP_ROOT.is_symlink() or project_root not in BACKUP_ROOT.resolve().parents:
        raise RuntimeError("项目备份目录指向项目外部或是符号链接；为保护数据，风险操作已取消")
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    final = BACKUP_ROOT / f"rmpp-{stamp}-{operation}-{uuid.uuid4().hex[:8]}.tar.gz"
    partial = final.with_suffix(final.suffix + ".partial")
    manifest_path = final.with_suffix(final.suffix + ".json")
    manifest_partial = manifest_path.with_suffix(manifest_path.suffix + ".partial")
    channel = None
    partial_created = final_created = manifest_partial_created = False
    try:
        if final.exists() or partial.exists() or manifest_path.exists() or manifest_partial.exists():
            raise RuntimeError("备份文件名冲突；为避免覆盖已有备份，风险操作已取消")
        command = "tar -cf - " + " ".join(shlex.quote(path) for path in paths)
        _stdin, stdout, stderr = client.exec_command(command, timeout=3600)
        channel = stdout.channel
        deadline = time.monotonic() + 3600
        raw = partial.open("xb")
        partial_created = True
        with raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            while True:
                if channel.recv_ready():
                    zipped.write(channel.recv(1024 * 1024))
                elif channel.exit_status_ready():
                    if not channel.recv_ready():
                        break
                else:
                    if time.monotonic() > deadline:
                        raise RuntimeError("RMPP 数据备份超过 60 分钟；风险操作已取消")
                    time.sleep(0.1)
            while channel.recv_ready():
                zipped.write(channel.recv(1024 * 1024))
        error = b""
        while channel.recv_stderr_ready():
            error += channel.recv_stderr(65536)
            if len(error) > 512 * 1024:
                break
        code = channel.recv_exit_status()
        if code:
            raise RuntimeError(f"RMPP 数据读取失败（tar 退出 {code}）；风险操作已取消：{error.decode('utf-8', 'replace')[-300:]}")
        with tarfile.open(partial, "r:gz") as archive:
            members = archive.getmembers()
            expected_prefix = "home/root/.local/share/remarkable/xochitl"
            if not any(member.name == expected_prefix or member.name.startswith(expected_prefix + "/") for member in members):
                raise RuntimeError("备份包未包含笔记数据库；风险操作已取消")
        digest = file_sha(partial)
        size = partial.stat().st_size
        partial.replace(final)
        partial_created = False
        final_created = True
        state = remote(client, "printf 'firmware='; sed -n 's/^IMG_VERSION=//p' /etc/os-release | tr -d '\"'; echo; printf 'arch='; uname -m")
        manifest = {"format": 1, "operation": operation, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "device_state": state.strip(), "paths": paths, "sha256": digest, "size_bytes": size,
                    "scope": "notes/documents, xochitl user config, XOVI/app install tree, rmtool, xochitl systemd unit/drop-ins",
                    "excludes": ["OS partitions", "SSH private keys", "unsaved in-memory edits"]}
        manifest_raw = manifest_partial.open("x", encoding="utf-8")
        manifest_partial_created = True
        with manifest_raw:
            manifest_raw.write(json.dumps(manifest, ensure_ascii=False, indent=2))
            manifest_raw.flush()
        manifest_partial.replace(manifest_path)
        manifest_partial_created = False
        log("device_snapshot_complete", operation=operation, archive=str(final), sha256=digest, size_bytes=size)
        progress(f"RMPP 数据备份完成：{final}\nSHA256：{digest}\n风险操作将继续。")
        return final
    except Exception:
        if channel:
            channel.close()
        if partial_created:
            partial.unlink(missing_ok=True)
        if final_created:
            final.unlink(missing_ok=True)
        if manifest_partial_created:
            manifest_partial.unlink(missing_ok=True)
        log("device_snapshot_failed", operation=operation)
        raise


def download(name: str) -> pathlib.Path:
    url, size, expected = SOURCES[name]
    path = CACHE / pathlib.PurePosixPath(url).name
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.stat().st_size != size or file_sha(path) != expected:
            raise RuntimeError(f"已有 {path.name} 校验不符；保留文件供检查")
        return path
    part = path.with_name(path.name + ".part")
    if part.exists():
        raise RuntimeError(f"存在上次未完成的下载：{part}；请先检查")
    request = urllib.request.Request(url, headers={"User-Agent": "RMPP-VNSee-Portable/1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, part.open("xb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        if part.stat().st_size != size or file_sha(part) != expected:
            raise RuntimeError(f"{name} 下载大小或 SHA256 不符")
        part.replace(path)
        log("download_verified", name=name, sha256=expected, size=size, url=url)
        return path
    except Exception:
        part.unlink(missing_ok=True)
        raise


def gzip_members(data: bytes) -> list[tuple[bytes, bytes]]:
    members = []
    while data:
        decoder = zlib.decompressobj(31)
        plain = decoder.decompress(data) + decoder.flush()
        consumed = len(data) - len(decoder.unused_data)
        if not decoder.eof or consumed <= 0:
            raise RuntimeError("APK gzip 流不完整")
        members.append((data[:consumed], plain))
        data = decoder.unused_data
    if len(members) != 3:
        raise RuntimeError("APK gzip 成员数不符")
    return members


def _tar_file(data: bytes, name: str) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        member = archive.getmember(name)
        if not member.isfile():
            raise RuntimeError(f"APK 条目不是文件：{name}")
        return archive.extractfile(member).read()


def verify_apk(apk: pathlib.Path, key: pathlib.Path) -> bytes:
    """Verify the pinned Vellum RSA signature and APK compressed datahash."""
    if file_sha(key) != KEY_SHA256:
        raise RuntimeError("Vellum 公钥哈希不符")
    if file_sha(apk) != SOURCES["vnsee"][2]:
        raise RuntimeError("VNSee APK 哈希不符")
    members = gzip_members(apk.read_bytes())
    signature = _tar_file(members[0][1], ".SIGN.RSA.packages.rsa.pub")
    public_key = serialization.load_pem_public_key(key.read_bytes())
    # Alpine APK v2 signs the compressed control member. The control member's
    # datahash then authenticates the compressed data member.
    public_key.verify(signature, members[1][0], padding.PKCS1v15(), hashes.SHA1())
    pkginfo = _tar_file(members[1][1], ".PKGINFO").decode("utf-8")
    fields = dict(line.split(" = ", 1) for line in pkginfo.splitlines() if " = " in line)
    required = {"pkgname": "vnsee-qtfb", "pkgver": "1.1.1-r0", "arch": "aarch64",
                "datahash": sha(members[2][0])}
    if any(fields.get(k) != v for k, v in required.items()):
        raise RuntimeError("APK 元数据或 payload datahash 不符")
    log("apk_signature_verified", apk_sha256=file_sha(apk), key_sha256=KEY_SHA256,
        payload_sha256=required["datahash"])
    return members[2][1]


def remote(client, command: str, timeout: int = 35) -> str:
    _, stdout, stderr = client.exec_command(command, timeout=timeout)
    status = stdout.channel.recv_exit_status()
    output = stdout.read().decode("utf-8", "replace")
    error = stderr.read().decode("utf-8", "replace")
    if status:
        raise RuntimeError(f"RMPP 命令失败({status}): {(error or output).strip()[:400]}")
    return output


def preflight(client) -> dict:
    script = (
        "printf 'probe_format=20261113-v3\\n'; "
        "set -eu; printf 'arch=%s\\n' \"$(uname -m)\"; "
        "printf 'firmware=%s\\n' \"$(sed -n 's/^IMG_VERSION=//p' /etc/os-release | tr -d '\"')\"; "
        "printf 'xochitl=%s\\n' \"$(systemctl is-active xochitl || true)\"; "
        "printf 'xovi=%s\\n' \"$([ -e /home/root/xovi ] && echo present || echo absent)\"; "
        "printf 'meta=%s\\n' \"$([ -e /home/root/.vnsee-portable ] && echo present || echo absent)\"; "
        "printf 'vnsee='; pidof vnsee || true; echo; "
        "printf 'qmd_mount=%s\\n' \"$(mountpoint -q /home/root/xovi/exthome/qt-resource-rebuilder && echo yes || echo no)\"; "
        "printf 'dropin_mount=%s\\n' \"$(mountpoint -q /etc/systemd/system/xochitl.service.d && echo yes || echo no)\"; "
        "printf 'rmtool=%s\\n' \"$([ -e /data/rmtool/xovi-standalone ] && echo present || echo absent)\"; "
        "printf 'rmtool_disabled=%s\\n' \"$([ -e /data/rmtool/disable-xovi ] && echo yes || echo no)\"; "
        "printf 'loaded_xovi='; grep -Fhl /xovi.so /proc/[0-9]*/maps 2>/dev/null | head -n 1 || true; echo; "
        "printf 'free_kib=%s\\n' \"$(df -Pk /home | awk 'END{print $4}')\"")
    result = dict(line.split("=", 1) for line in remote(client, script).splitlines() if "=" in line)
    if result.get("arch") != "aarch64" or result.get("firmware") != FIRMWARE:
        raise RuntimeError(f"仅验证过 RMPP 固件 {FIRMWARE}；当前 {result.get('arch')} / {result.get('firmware')}")
    if result.get("xochitl") != "active":
        raise RuntimeError("xochitl 未运行；拒绝安装")
    if result.get("vnsee") or result.get("qmd_mount") != "no" or result.get("dropin_mount") != "no" or result.get("loaded_xovi"):
        blockers = {
            key: result.get(key, "未读取")
            for key in ("vnsee", "qmd_mount", "dropin_mount", "loaded_xovi")
        }
        log("preflight_blocked_runtime", **blockers)
        details = ", ".join(f"{key}={value or '无'}" for key, value in blockers.items())
        raise RuntimeError(f"设备仍有 VNSee 或 XOVI 临时运行态；请先安全恢复 stock（格式 20261113-v3；{details}）")
    if result.get("rmtool") == "present" and result.get("rmtool_disabled") != "yes":
        raise RuntimeError("rmtool XOVI 仍启用；拒绝同时安装另一套 XOVI")
    if int(result.get("free_kib", "0")) < 50000:
        raise RuntimeError("/home 可用空间不足 50 MiB")
    log("preflight", arch=result["arch"], firmware=result["firmware"], rmtool=result["rmtool"])
    return result


def read_device_hashtab(client) -> bytes | None:
    """Read a hashtab generated on this device by the official XOVI tool."""
    path = ROOT + "/exthome/qt-resource-rebuilder/hashtab"
    if remote(client, "test -s " + shlex.quote(path) + " && echo yes || echo no").strip() != "yes":
        return None
    sftp = client.open_sftp()
    try:
        with sftp.open(path, "rb") as stream:
            data = stream.read(2_000_001)
    finally:
        sftp.close()
    if len(data) > 2_000_000 or len(data) < 1000:
        raise RuntimeError("现有 hashtab 大小异常")
    return data


def read_receipt(client) -> dict:
    sftp = client.open_sftp()
    try:
        try:
            with sftp.open(META + "/install-receipt.json", "rb") as stream:
                receipt = json.loads(stream.read().decode("utf-8"))
        except OSError as exc:
            if getattr(exc, "errno", None) == 2:
                raise RuntimeError(
                    f"找不到本安装器的设备收据 {META}/install-receipt.json；"
                    "为避免运行其他 XOVI 的 stock 脚本，已停止恢复"
                ) from exc
            raise
    finally:
        sftp.close()
    if (receipt.get("format") != 2 or receipt.get("owner") != "RMPP-VNSee-Portable"
            or receipt.get("root") != ROOT or receipt.get("firmware") != FIRMWARE
            or not isinstance(receipt.get("files"), dict) or not isinstance(receipt.get("links"), dict)):
        raise RuntimeError("设备收据不属于本安装器")
    return receipt


def _read_remote_json(client, path: str) -> dict:
    sftp = client.open_sftp()
    try:
        with sftp.open(path, "rb") as stream:
            value = json.loads(stream.read().decode("utf-8"))
    finally:
        sftp.close()
    if (value.get("format") != 2 or value.get("owner") != "RMPP-VNSee-Portable"
            or value.get("root") != ROOT or value.get("firmware") != FIRMWARE
            or not isinstance(value.get("files"), dict) or not isinstance(value.get("links"), dict)):
        raise RuntimeError("设备收据不属于本安装器")
    return value


def _cleanup_incomplete_install(client, root_exists: bool) -> None:
    """Clean only verifiable installer staging artifacts after an interrupted install."""
    if remote(client, f"test -d {META} && test ! -L {META} && echo yes || echo no").strip() == "no":
        return
    names = remote(client, f"ls -A1 {shlex.quote(META)}").splitlines()
    for name in names:
        if name == "install-receipt.json":
            if root_exists:
                continue
            if len(names) != 1:
                raise RuntimeError("无设备目录的安装记录与其他内容并存；保留供检查")
            _read_remote_json(client, META + "/install-receipt.json")
            remote(client, f"rm -- {shlex.quote(META + '/install-receipt.json')}; rmdir {shlex.quote(META)}")
            continue
        if not re.fullmatch(r"stage-[0-9a-f]{12}", name):
            raise RuntimeError(f"安装元数据中有未知内容，保留不动：{name}")
        stage = META + "/" + name
        if remote(client, f"test -d {shlex.quote(stage)} && test ! -L {shlex.quote(stage)} && echo yes || echo no").strip() != "yes":
            raise RuntimeError(f"暂存路径类型异常，保留不动：{name}")
        entries = remote(client, f"ls -A1 {shlex.quote(stage)}").splitlines()
        if not entries:
            remote(client, f"rmdir {shlex.quote(stage)}")
            continue
        if entries != ["bundle.tar.gz", "install-receipt.json"]:
            raise RuntimeError(f"暂存目录包含未识别内容，保留不动：{name}")
        receipt = _read_remote_json(client, stage + "/install-receipt.json")
        bundle_path = stage + "/bundle.tar.gz"
        if remote(client, f"sha256sum {shlex.quote(bundle_path)}").split()[0] != receipt.get("bundle_sha256"):
            raise RuntimeError(f"暂存包哈希不符，保留不动：{name}")
        if root_exists:
            # The installer renames the tree before promoting its receipt. Recover the
            # receipt only when every installed path still matches its recorded hash.
            if remote(client, f"test -e {META}/install-receipt.json && echo yes || echo no").strip() == "yes":
                verify_tree(client, read_receipt(client))
            else:
                verify_tree(client, receipt)
                remote(client, f"mv {shlex.quote(stage + '/install-receipt.json')} {shlex.quote(META + '/install-receipt.json')}")
            remote(client, f"rm -- {shlex.quote(bundle_path)}; rmdir {shlex.quote(stage)}")
        else:
            # No install tree was committed; this directory is solely the validated
            # package staged by this installer's atomic install routine.
            remote(client, f"rm -r -- {shlex.quote(stage)}")
    if remote(client, f"test -d {META} && test -z \"$(ls -A1 {shlex.quote(META)})\" && echo empty || echo nonempty").strip() == "empty":
        remote(client, f"rmdir {shlex.quote(META)}")


def build_bundle(paths: dict[str, pathlib.Path], payload: bytes, hashtab: bytes | None = None) -> tuple[pathlib.Path, dict]:
    """Prepare only the files owned by this installer, without tar extraction."""
    bundle_dir = PROJECT / "deploy" / "portable-bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle = bundle_dir / "xovi-appload-vnsee.tar.gz"
    files, links = {}, {}

    def add(out, name: str, data: bytes, mode=0o644):
        if name in files or name in links or not name.startswith("xovi/"):
            raise RuntimeError(f"重复或越界文件：{name}")
        info = tarfile.TarInfo(name)
        info.size, info.mode, info.mtime = len(data), mode, 0
        out.addfile(info, io.BytesIO(data))
        files[name] = sha(data)

    with bundle.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as out:
        with tarfile.open(paths["xovi"], "r:gz") as archive:
            for item in archive:
                name = item.name.rstrip("/")
                if name != "xovi" and (not name.startswith("xovi/") or ".." in pathlib.PurePosixPath(name).parts):
                    raise RuntimeError(f"XOVI 路径越界：{name}")
                if item.isdir():
                    continue
                if item.issym():
                    if (name, item.linkname) not in {
                        ("xovi/services/xochitl.service/exthome", ROOT + "/exthome"),
                        ("xovi/services/xochitl.service/extensions.d", ROOT + "/extensions.d"),
                    }:
                        raise RuntimeError(f"未允许的 XOVI 链接：{name}")
                    info = tarfile.TarInfo(name)
                    info.type, info.linkname, info.mode = tarfile.SYMTYPE, item.linkname, 0o777
                    out.addfile(info)
                    links[name] = item.linkname
                elif item.isfile():
                    add(out, name, archive.extractfile(item).read(), item.mode)
                else:
                    raise RuntimeError(f"未知 XOVI 条目：{name}")
        with tarfile.open(paths["appload"], "r:gz") as archive:
            for item in archive:
                if item.isdir():
                    continue
                if not item.isfile():
                    raise RuntimeError(f"未知 AppLoad 条目：{item.name}")
                if item.name == "appload.so":
                    add(out, "xovi/extensions.d/appload.so", archive.extractfile(item).read(), item.mode)
                elif item.name in ("shims/qtfb-shim.so", "shims/qtfb-shim-32bit.so"):
                    add(out, "xovi/exthome/appload/" + item.name, archive.extractfile(item).read(), item.mode)
                else:
                    raise RuntimeError(f"未知 AppLoad 文件：{item.name}")
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
            prefix = "home/root/xovi/exthome/appload/"
            elf = _tar_file(payload, prefix + "vnsee/vnsee")
            if sha(elf) != ELF_SHA256 or elf[:4] != b"\x7fELF" or elf[18:20] != b"\xb7\x00":
                raise RuntimeError("VNSee ELF 架构或哈希不符")
            base = "xovi/exthome/appload/vnsee-asivery-test/"
            add(out, base + "vnsee", elf, 0o755)
            add(out, base + "icon.png", archive.extractfile(prefix + "vnsee-0/icon.png").read())
            add(out, base + "LICENSE", archive.extractfile("home/root/.vellum/licenses/vnsee-qtfb/LICENSE").read())
            add(out, base + "SOURCES", archive.extractfile("home/root/.vellum/licenses/vnsee-qtfb/SOURCES").read())
            manifest = {"name": "VNSee asivery Test", "application": "vnsee", "supportsVirtualKeyboard": True,
                        "environment": {"VNSEE_WAVEFORM_MODE": "STANDARD", "VNSEE_ENCODING": "COPYRECT"},
                        "args": ["localhost"], "qtfb": True}
            add(out, base + "external.manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
        if hashtab is not None:
            add(out, "xovi/exthome/qt-resource-rebuilder/hashtab", hashtab, 0o600)
        qmd = PROJECT / "deploy" / "qmd-vnsee-layout" / "vnsee-asivery-clip-v7-landscape.qmd"
        add(out, "xovi/exthome/qt-resource-rebuilder/vnsee-asivery-clip-v7-landscape.qmd", qmd.read_bytes())
    if any(file.startswith(link + "/") for file in files for link in links):
        raise RuntimeError("安装包文件位于符号链接之下；拒绝提取")
    receipt = {"format": 2, "owner": "RMPP-VNSee-Portable", "root": ROOT, "files": files, "links": links,
               "firmware": FIRMWARE, "bundle_sha256": file_sha(bundle),
               "hashtab_sha256": sha(hashtab) if hashtab is not None else None,
               "sources": {k: v[2] for k, v in SOURCES.items()}}
    (bundle_dir / "install-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return bundle, receipt


def prepare(client, progress=lambda text: None) -> tuple[pathlib.Path, dict]:
    """Read-only device check plus Windows downloads; no device mutation."""
    state = preflight(client)
    if state["xovi"] != "absent" or state["meta"] != "absent":
        raise RuntimeError("已有 XOVI 或安装记录；拒绝覆盖")
    # A fresh device has no hashtab. Install the files, then stop before XOVI
    # activation. A guided official rebuild can complete the setup later.
    hashtab = None
    paths = {}
    for name in SOURCES:
        progress(f"校验或下载 {name} 到 Windows…")
        paths[name] = download(name)
    payload = verify_apk(paths["vnsee"], paths["vellum_key"])
    return build_bundle(paths, payload, hashtab)


def install(client, progress=lambda text: None) -> dict:
    bundle, receipt = prepare(client, progress)
    backup_device_data(client, "install", progress)
    stage = META + "/stage-" + uuid.uuid4().hex[:12]
    remote(client, f"set -eu; test ! -e {ROOT}; test ! -e {META}; mkdir -m 700 {META}; mkdir -m 700 {stage}")
    sftp = client.open_sftp()
    try:
        progress("经 USB SSH 上传已验证的离线包…")
        sftp.put(str(bundle), stage + "/bundle.tar.gz")
        with sftp.open(stage + "/install-receipt.json", "wb") as stream:
            stream.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True).encode())
    finally:
        sftp.close()
    if remote(client, f"sha256sum {stage}/bundle.tar.gz").split()[0] != receipt["bundle_sha256"]:
        raise RuntimeError("上传后的包哈希不同；未解包")
    # Extract only the verified bundle and atomically claim an absent root.
    remote(client, f"set -eu; tar -tzf {stage}/bundle.tar.gz >/dev/null; "
                   f"tar -xzf {stage}/bundle.tar.gz -C {stage}; test ! -e {ROOT}; "
                   f"mv {stage}/xovi {ROOT}")
    try:
        verify_tree(client, receipt)
        remote(client, f"set -eu; mv {stage}/install-receipt.json {META}/install-receipt.json; "
                       f"rm {stage}/bundle.tar.gz; rmdir {stage}; systemctl is-active --quiet xochitl")
    except Exception:
        log("install_incomplete", stage=stage)
        raise RuntimeError("安装文件校验未完成；设备保留文件供检查，XOVI 未启动")
    log("installed_pending_hashtab", bundle_sha256=receipt["bundle_sha256"], files=len(receipt["files"]))
    return receipt


def complete_hashtab(client, verified_generation: bool = False, progress=lambda text: None) -> dict:
    """Record a hashtab only after this process verified the official tool."""
    state = preflight(client)
    if state["xovi"] != "present" or state["meta"] != "present":
        raise RuntimeError("未找到本安装器部署的文件")
    receipt = read_receipt(client)
    path = "xovi/exthome/qt-resource-rebuilder/hashtab"
    if path in receipt["files"]:
        verify_tree(client, receipt)
        return receipt
    if not verified_generation:
        raise RuntimeError("尚未生成设备 hashtab；请点击生成按钮运行官方工具")
    data = read_device_hashtab(client)
    if data is None:
        raise RuntimeError("尚未生成设备 hashtab；请先使用 XOVI 官方工具，并在 stock 界面恢复后重试")
    candidate = dict(receipt)
    candidate["files"] = dict(receipt["files"])
    candidate["files"][path] = sha(data)
    candidate["hashtab_sha256"] = sha(data)
    verify_tree(client, candidate)
    backup_device_data(client, "record-hashtab", progress)
    sftp = client.open_sftp()
    try:
        temp = META + "/install-receipt.new"
        with sftp.open(temp, "wb") as stream:
            stream.write(json.dumps(candidate, ensure_ascii=False, sort_keys=True).encode())
    finally:
        sftp.close()
    remote(client, f"set -eu; mv {META}/install-receipt.new {META}/install-receipt.json")
    log("hashtab_recorded", sha256=sha(data), size=len(data))
    return candidate


def generate_hashtab(client, progress=lambda text: None) -> dict:
    """Run the pinned official XOVI one-time builder after explicit consent.

    The script stops xochitl and temporarily runs it with QMLDiff. The caller
    must warn about unsaved notes and ask for approval before calling this.
    """
    state = preflight(client)
    if state["xovi"] != "present" or state["meta"] != "present":
        raise RuntimeError("请先安装本安装器的离线文件")
    receipt = read_receipt(client)
    if receipt.get("hashtab_sha256"):
        verify_tree(client, receipt)
        return receipt
    verify_tree(client, receipt)
    script_hash = receipt["files"].get("xovi/rebuild_hashtable")
    if not script_hash or remote(client, "sha256sum /home/root/xovi/rebuild_hashtable").split()[0] != script_hash:
        raise RuntimeError("XOVI 官方 hashtab 构建脚本已变化")
    backup_device_data(client, "generate-hashtab", progress)
    progress("XOVI 正在生成设备专用 hashtab；如设备要求，请在 RMPP 上输入设备密码…")
    log("hashtab_generation_started", firmware=FIRMWARE, script_sha256=script_hash)
    # The pinned script contains one read prompt. Supply only its Enter key;
    # the device password, if requested, is entered on the tablet itself.
    _, stdout, stderr = client.exec_command("printf '\\n' | /home/root/xovi/rebuild_hashtable", timeout=300)
    try:
        channel = stdout.channel
        chunks, errors = [], []
        deadline = time.monotonic() + 300
        while not channel.exit_status_ready():
            if channel.recv_ready():
                chunks.append(channel.recv(65536))
            if channel.recv_stderr_ready():
                errors.append(channel.recv_stderr(65536))
            if time.monotonic() > deadline:
                raise RuntimeError("设备端 hashtab 构建超过 5 分钟，运行状态未确认")
            time.sleep(0.2)
        while channel.recv_ready():
            chunks.append(channel.recv(65536))
        while channel.recv_stderr_ready():
            errors.append(channel.recv_stderr(65536))
        code = channel.recv_exit_status()
        output = b"".join(chunks).decode("utf-8", "replace")
        error = b"".join(errors).decode("utf-8", "replace")
        if code or "Hashtab saved to" not in output:
            raise RuntimeError(f"hashtab 构建未确认完成（退出 {code}）：{error[-180:]}")
    except Exception:
        log("hashtab_generation_unconfirmed")
        try:
            remote(client, "if ! systemctl is-active --quiet xochitl && "
                           "! mountpoint -q /etc/systemd/system/xochitl.service.d && "
                           "test -z \"$(pidof xochitl || true)\"; then "
                           "systemctl start xochitl; fi")
        except Exception:
            pass
        raise RuntimeError("hashtab 生成未确认；请检查设备 xochitl 状态，不要直接启动 XOVI")
    # The official script leaves the systemd service stopped after the
    # temporary QMLDiff run. Start the stock service once and verify it.
    remote(client, "set -eu; systemctl start xochitl; systemctl is-active --quiet xochitl", timeout=90)
    result = complete_hashtab(client, verified_generation=True, progress=progress)
    log("hashtab_generation_complete", sha256=result["hashtab_sha256"])
    return result


def activate(client, progress=lambda text: None) -> None:
    """Start only the owned XOVI tree after explicit UI approval.

    This interrupts xochitl. The caller must ask the user to save notes first.
    """
    state = preflight(client)
    if state["xovi"] != "present" or state["meta"] != "present":
        raise RuntimeError("XOVI 未由本安装器部署")
    receipt = read_receipt(client)
    if not receipt.get("hashtab_sha256"):
        raise RuntimeError("尚未完成设备专用 hashtab；不能启动 XOVI")
    verify_tree(client, receipt)
    remote(client, "set -eu; test -x /home/root/xovi/start; test -x /home/root/xovi/stock; "
                   "test -s /home/root/xovi/exthome/qt-resource-rebuilder/hashtab; "
                   "test ! -e /etc/systemd/system/xochitl.service.d/00-xovi.conf")
    # Store the currently visible persistent unit in the local log; XOVI's
    # stock script must uncover exactly this unit after unmounting tmpfs.
    before = remote(client, "sha256sum /etc/systemd/system/xochitl.service.d/*.conf 2>/dev/null || true")
    log("activation_before", persistent_dropins=before.strip())
    backup_device_data(client, "activate-xovi", progress)
    try:
        remote(client, "set -eu; /home/root/xovi/start; systemctl is-active --quiet xochitl", timeout=90)
        loaded = remote(client, "grep -Fhl /home/root/xovi/xovi.so /proc/[0-9]*/maps 2>/dev/null | head -n 1")
        if not loaded:
            raise RuntimeError("XOVI 未出现在 xochitl 运行映射中")
    except Exception as exc:
        log("activation_failed", error=str(exc)[:200])
        try:
            restore_stock(client, progress)
        except Exception as recovery_error:
            log("activation_recovery_failed", error=str(recovery_error)[:200])
            raise RuntimeError("XOVI 启动失败且自动恢复未确认；请通过 USB SSH 检查状态，勿重复启动") from exc
        raise RuntimeError("XOVI 启动未通过验证，已按本安装收据恢复 stock；勿重复启动") from exc
    log("activated", firmware=FIRMWARE)


def owned_active(client) -> bool:
    """Recognize only the temporary XOVI runtime installed by this project."""
    mounted = remote(client, "mountpoint -q /etc/systemd/system/xochitl.service.d && echo yes || echo no").strip()
    if mounted == "no":
        return False
    if remote(client, "findmnt -n -o FSTYPE /etc/systemd/system/xochitl.service.d").strip() != "tmpfs":
        raise RuntimeError("systemd drop-in 挂载不是预期 tmpfs")
    remote(client, "set -eu; grep -Fqx 'Environment=\"LD_PRELOAD=/home/root/xovi/xovi.so\"' "
                   "/etc/systemd/system/xochitl.service.d/00-xovi.conf; "
                   "grep -Fhl /home/root/xovi/xovi.so /proc/[0-9]*/maps 2>/dev/null | head -n 1 | grep -q .")
    return True


def restore_stock(client, progress=lambda text: None) -> None:
    """Use only this install's verified stock script; refuse unknown mounts."""
    receipt = read_receipt(client)
    if receipt.get("firmware") != FIRMWARE:
        raise RuntimeError("固件与安装记录不同")
    stock_hash = receipt["files"].get("xovi/stock")
    if not stock_hash or remote(client, "sha256sum /home/root/xovi/stock").split()[0] != stock_hash:
        raise RuntimeError("stock 脚本与安装记录不同")
    mount_state = remote(client, "if mountpoint -q /etc/systemd/system/xochitl.service.d; "
                                "then findmnt -n -o FSTYPE /etc/systemd/system/xochitl.service.d; "
                                "else echo absent; fi").strip()
    if mount_state == "absent":
        if remote(client, "grep -Fhl /home/root/xovi/xovi.so /proc/[0-9]*/maps 2>/dev/null | head -n 1").strip():
            raise RuntimeError("XOVI 仍在运行，但未发现预期挂载；拒绝自动恢复")
        return
    if mount_state != "tmpfs":
        raise RuntimeError("systemd drop-in 不是预期 tmpfs；拒绝卸载未知挂载")
    backup_device_data(client, "restore-stock", progress)
    remote(client, "set -eu; test -f /etc/systemd/system/xochitl.service.d/00-xovi.conf; "
                   "grep -Fqx 'Environment=\"LD_PRELOAD=/home/root/xovi/xovi.so\"' "
                   "/etc/systemd/system/xochitl.service.d/00-xovi.conf; "
                   "test -z \"$(pidof vnsee || true)\"; /home/root/xovi/stock; "
                   "systemctl is-active --quiet xochitl", timeout=90)
    if remote(client, "mountpoint -q /etc/systemd/system/xochitl.service.d && echo yes || echo no").strip() != "no":
        raise RuntimeError("stock 执行后 systemd 临时挂载仍存在")
    log("stock_restored")


def verify_tree(client, receipt: dict) -> None:
    expected_files = receipt["files"]
    lines = remote(client, f"set -eu; test -d {ROOT}; test ! -L {ROOT}; "
                   f"find {ROOT} -type f; echo __LINKS__; find {ROOT} -type l").splitlines()
    if "__LINKS__" not in lines:
        raise RuntimeError("设备文件清单格式异常")
    pivot = lines.index("__LINKS__")
    files, links = {}, {}
    for path in lines[:pivot]:
        if not path.startswith(ROOT + "/") or any(c in path for c in "\r\n\t"):
            raise RuntimeError("设备文件路径越界")
        files["xovi/" + path[len(ROOT) + 1:]] = remote(client, "sha256sum " + shlex.quote(path)).split()[0]
    for path in lines[pivot + 1:]:
        if not path.startswith(ROOT + "/") or any(c in path for c in "\r\n\t"):
            raise RuntimeError("设备链接路径越界")
        links["xovi/" + path[len(ROOT) + 1:]] = remote(client, "readlink " + shlex.quote(path)).strip()
    if files != expected_files or links != receipt["links"]:
        raise RuntimeError("设备文件与安装清单不一致；拒绝后续操作")


def uninstall(client, progress=lambda text: None) -> None:
    """Uninstall only an exact owned tree; never adopt legacy installations."""
    if owned_active(client):
        restore_stock(client, progress)
    state = preflight(client)
    if state["xovi"] == "absent":
        if state["meta"] == "present":
            backup_device_data(client, "remove-staging", progress)
            _cleanup_incomplete_install(client, root_exists=False)
            if remote(client, f"test -e {META} && echo yes || echo no").strip() == "yes":
                raise RuntimeError("设备仍有未能安全识别的安装元数据；已保留供检查")
        return
    if state["meta"] != "present":
        raise RuntimeError("缺少本安装器的收据；拒绝删除现有 XOVI")
    _cleanup_incomplete_install(client, root_exists=True)
    receipt = read_receipt(client)
    verify_tree(client, receipt)
    meta_listing = remote(client, f"ls -A1 {META}").splitlines()
    if meta_listing != ["install-receipt.json"]:
        raise RuntimeError("安装记录目录包含未知内容；拒绝删除")
    # No persistent unit is changed. An inactive tree can be removed only after
    # its exact ownership, every file hash, and stock runtime are checked.
    backup_device_data(client, "uninstall", progress)
    remote(client, f"set -eu; test ! -L {ROOT}; test ! -L {META}; "
                   f"test ! -e {META}/removed; mv {ROOT} {META}/removed; "
                   f"systemctl is-active --quiet xochitl")
    try:
        remote(client, f"set -eu; rm -r -- {META}/removed; rm -- {META}/install-receipt.json; rmdir {META}")
    except Exception:
        remote(client, f"if test -d {META}/removed && test ! -e {ROOT}; then mv {META}/removed {ROOT}; fi")
        raise
    log("uninstalled", files=len(receipt["files"]))
