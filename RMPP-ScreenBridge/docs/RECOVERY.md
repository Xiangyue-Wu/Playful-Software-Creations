# Recovery after an interrupted run

Save unsynced notes before any xochitl restart. Keep USB SSH available. The wizard's **恢复 stock 界面** button is the first recovery option.

If the GUI cannot connect, inspect the tablet through SSH before changing anything:

```sh
systemctl is-active xochitl
mountpoint /etc/systemd/system/xochitl.service.d
findmnt -n -o FSTYPE /etc/systemd/system/xochitl.service.d
cat /etc/systemd/system/xochitl.service.d/00-xovi.conf
sha256sum /home/root/xovi/stock
```

Only if the mount is `tmpfs`, `00-xovi.conf` names `/home/root/xovi/xovi.so`, and the stock script hash matches `xovi/stock` in `/home/root/.vnsee-portable/install-receipt.json`, run the pinned XOVI stock script once:

```sh
/home/root/xovi/stock
systemctl is-active xochitl
```

Do not run this against a different XOVI installation or an unknown mount. Do not remove rmtool's drop-in or `disable-xovi` marker. If hashtab generation was interrupted and the service is stopped **without** a temporary XOVI mount, start only stock xochitl with `systemctl start xochitl` and verify its state. If the current state does not match these checks, stop and preserve logs; do not repeat startup or delete device files.

Before a risky project operation, the wizard creates a local archive under `临时备份/RMPP/`. It includes the notebook database, user config, project-managed `/home/root/xovi`, the project's receipt, `/data/rmtool` when present, and the xochitl unit/drop-ins. Each archive has a JSON sidecar and SHA256. It is a scoped data/config snapshot, not a full OS image; it omits SSH private keys and cannot capture note edits that have not reached disk. Keep enough Windows disk space and save open notes before restarting xochitl. The `临时备份/` folder is Git-ignored and must never be published.

Run the standalone `卸载RMPP-ScreenBridge.cmd`. Device uninstall requires working USB SSH, stock `xochitl`, no VNSee process, no unknown temporary mount, and an exact project receipt plus every file/symlink hash. The uninstaller can remove a verifiable interrupted staging bundle; unknown or modified files are left in place and reported. If USB/SSH is unavailable, choose Windows-only cleanup and retry device removal after connectivity returns. No remote uninstaller can remove files while the tablet is unreachable. The Windows cleanup removes only pinned project downloads, the matching install bundle/receipt, project logs, and this project's credential entry; `.venv` is scheduled for removal after the UI exits. It intentionally keeps the source, uninstaller, shared `known_hosts`, user notes, rmtool files, and anything it cannot verify.
