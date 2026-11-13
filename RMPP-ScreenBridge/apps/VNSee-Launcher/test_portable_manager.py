"""Offline safety-gate tests; no SSH connection or device mutation."""
import unittest
from unittest.mock import patch

import portable_manager as manager


BASE = (
    "arch=aarch64\nfirmware=3.29.0.153\nxochitl=active\n"
    "xovi=absent\nmeta=absent\nvnsee=\nqmd_mount=no\n"
    "dropin_mount=no\nrmtool=present\nrmtool_disabled=yes\n"
    "loaded_xovi=\nfree_kib=200000\n"
)


class PreflightTests(unittest.TestCase):
    def check_state(self, output):
        with patch.object(manager, "remote", return_value=output), patch.object(manager, "log"):
            return manager.preflight(object())

    def test_supported_stock_profile(self):
        self.assertEqual(self.check_state(BASE)["firmware"], manager.FIRMWARE)

    def test_unknown_firmware_refused(self):
        with self.assertRaisesRegex(RuntimeError, "仅验证过"):
            self.check_state(BASE.replace("3.29.0.153", "3.30.0"))

    def test_active_rmtool_refused(self):
        with self.assertRaisesRegex(RuntimeError, "rmtool XOVI"):
            self.check_state(BASE.replace("rmtool_disabled=yes", "rmtool_disabled=no"))

    def test_loaded_xovi_refused(self):
        with self.assertRaisesRegex(RuntimeError, "临时运行态"):
            self.check_state(BASE.replace("loaded_xovi=\n", "loaded_xovi=/proc/123/maps\n"))

    def test_active_vnsee_refused(self):
        with self.assertRaisesRegex(RuntimeError, "临时运行态"):
            self.check_state(BASE.replace("vnsee=\n", "vnsee=123\n"))

    def test_unverified_hashtab_refused(self):
        receipt = {"files": {}, "hashtab_sha256": None}
        with patch.object(manager, "preflight", return_value={"xovi": "present", "meta": "present"}), \
             patch.object(manager, "read_receipt", return_value=receipt), \
             patch.object(manager, "read_device_hashtab") as read:
            with self.assertRaisesRegex(RuntimeError, "尚未生成设备 hashtab"):
                manager.complete_hashtab(object())
            read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
