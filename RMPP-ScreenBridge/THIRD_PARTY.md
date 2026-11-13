# Upstream projects and attribution

| Project | Role here | Upstream license | Included in this source snapshot? |
| --- | --- | --- | --- |
| [matteodelabre/vnsee](https://github.com/matteodelabre/vnsee) | Original VNSee project | GPL-3.0, as carried by the fork | No |
| [asivery/vnsee](https://github.com/asivery/vnsee) | QTFB VNSee client; Vellum package built from commit `704af75bb5f053f052683d2db8d5ddfe4f50a7d2` | GPL-3.0 | No binary or C++ source |
| [asivery/rm-appload](https://github.com/asivery/rm-appload) | AppLoad and QTFB; the QMD targets its window resource | GPL-3.0 | No binary or source tree |
| [asivery/rm-xovi-extensions](https://github.com/asivery/rm-xovi-extensions) | XOVI extensions and qt-resource-rebuilder | GPL-3.0 | No binary or source tree |
| [asivery/xovi](https://github.com/asivery/xovi) | XOVI runtime framework | LGPL-3.0 | No binary or source tree |
| [asivery/qmldiff](https://github.com/asivery/qmldiff) | Tool used to validate QMD syntax | GPL-3.0 | No tool binary or source tree |
| [vellum-dev/vellum](https://github.com/vellum-dev/vellum) | Official VNSee package recipe and signed package repository | MIT for infrastructure; packages retain their own licenses | No APK or package manager |
| [TightVNC 2](https://www.tightvnc.com/licensing.php) | Independent Windows VNC server | GNU GPL version 2 | No installer or executable |

External Python dependencies are listed in `requirements.txt` and are not vendored. This project is not endorsed by any of the upstream authors or reMarkable.

The QMD and Windows setup wizard are integration work. The QMD changes how an existing AppLoad QML resource is patched at runtime; it does not include a copy of that resource. Preserve upstream notices and provide corresponding source if you later distribute upstream GPL binaries or modified upstream code.
