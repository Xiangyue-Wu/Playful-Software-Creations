# Upstream projects and licenses

## Device-side software

| Project | Use | License | Included in release ZIP? |
| --- | --- | --- | --- |
| [asivery/vnsee](https://github.com/asivery/vnsee) | VNSee QTFB client; Vellum package recipe pins commit `704af75bb5f053f052683d2db8d5ddfe4f50a7d2` | GPL-3.0 | No; downloaded and verified by the Windows app |
| [asivery/rm-appload](https://github.com/asivery/rm-appload) | AppLoad/QTFB runtime | GPL-3.0 | No; downloaded by the Windows app |
| [asivery/rm-xovi-extensions](https://github.com/asivery/rm-xovi-extensions) | XOVI extensions | GPL-3.0 | No; downloaded by the Windows app |
| [asivery/xovi](https://github.com/asivery/xovi) | XOVI framework | LGPL-3.0 | No; downloaded by the Windows app |
| [vellum-dev/vellum](https://github.com/vellum-dev/vellum) | Official package recipe and signed package repository | MIT for infrastructure; packages retain their own licenses | No package manager or APK is bundled |

## Windows application and release build

The release executable bundles CPython and the pinned Python runtime dependencies from `requirements.txt`. Their licenses and source are available from the linked projects and PyPI metadata:

| Project | Version in release build | License | Project |
| --- | --- | --- | --- |
| [Paramiko](https://www.paramiko.org/) | 5.1.0 | LGPL-2.1 | [Source](https://github.com/paramiko/paramiko) |
| [pywin32](https://github.com/mhammond/pywin32) | 311 | PSF | [Source](https://github.com/mhammond/pywin32) |
| [cryptography](https://cryptography.io/) | 44.0.1 | Apache-2.0 / BSD-3-Clause | [Source](https://github.com/pyca/cryptography) |
| [bcrypt](https://github.com/pyca/bcrypt/) | 5.0.0 | Apache-2.0 | Source |
| [Invoke](https://www.pyinvoke.org/) | 3.0.3 | BSD-2-Clause | [Source](https://github.com/pyinvoke/invoke) |
| [PyNaCl](https://pynacl.readthedocs.io/) | 1.6.2 | Apache-2.0 | [Source](https://github.com/pyca/pynacl) |
| [cffi](https://cffi.readthedocs.io/) | 2.1.1 | MIT-0 | [Source](https://github.com/python-cffi/cffi) |
| [pycparser](https://github.com/eliben/pycparser) | 3.12 | BSD-3-Clause | Source |
| CPython | 3.13.2 | PSF License | [Source and license](https://www.python.org/downloads/source/) |
| PyInstaller | 6.22.3 (build tool) | GPL-2.0-or-later with bootloader exception | [Source and license](https://github.com/pyinstaller/pyinstaller) |

The executable contains the Python runtime and the listed modules. Each retains its own license and copyright; the exact package versions used are recorded in `BUILD-INFO.txt`.

## Other tools

| Project | Use | License | Included? |
| --- | --- | --- | --- |
| [TightVNC 2](https://www.tightvnc.com/licensing.php) | Windows VNC server used by the user | GPL-2.0 | No installer or executable |
| [asivery/qmldiff](https://github.com/asivery/qmldiff) | Used to validate the QMD during development | GPL-3.0 | No |

The QMD and Windows installer are integration work; no copy of AppLoad's QML resource is included. This project is not endorsed by reMarkable or upstream maintainers. Preserve all upstream notices when redistributing or modifying upstream software.
