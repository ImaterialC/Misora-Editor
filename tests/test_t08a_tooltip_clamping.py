import ctypes
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import misora
from misora import DIALOGUE_MAX_DIGITS, DIALOGUE_MAX_LINES, MisoraApp


class _T08aTooltipTestBase(unittest.TestCase):
    """Shared MisoraApp harness for T-08a ToolTip clamping probes and guards."""

    def setUp(self) -> None:
        self._orig_config_path = misora.CONFIG_PATH
        self.temp_dir = Path(tempfile.mkdtemp(prefix="misora_t08a_"))
        self.config_path = self.temp_dir / "misora_config.json"
        self.config_path.write_text("{}", encoding="utf-8")
        misora.CONFIG_PATH = self.config_path
        self.app = None
        with mock.patch.object(misora, "messagebox"):
            self.app = MisoraApp(restore_session=False, show_splash=False)
            self.app.update_idletasks()

    def tearDown(self) -> None:
        try:
            if self.app is not None:
                try:
                    tip = getattr(self.app.lbl_char_overflow, "_tooltip", None)
                    if tip is not None:
                        tip.hide_tip()
                except Exception:
                    pass
                try:
                    self.app.destroy()
                except Exception:
                    pass
        finally:
            misora.CONFIG_PATH = self._orig_config_path
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _show_and_measure_tip(
        self,
        *,
        work_area: tuple[int, int, int, int],
        rootx: int,
        rooty: int,
        height: int,
    ) -> tuple[int, int, int, int]:
        """Show lbl_char_overflow tooltip under mocked geometry and return (x, y, tip_w, tip_h)."""
        tip = self.app.lbl_char_overflow._tooltip
        tip.hide_tip()
        with mock.patch.object(misora, "_get_work_area", create=True, return_value=work_area), \
             mock.patch.object(tip.widget, "winfo_rootx", return_value=rootx), \
             mock.patch.object(tip.widget, "winfo_rooty", return_value=rooty), \
             mock.patch.object(tip.widget, "winfo_height", return_value=height):
            tip.show_tip()
            self.assertIsNotNone(tip.tip_window)
            tip.tip_window.update_idletasks()
            x = tip.tip_window.winfo_x()
            y = tip.tip_window.winfo_y()
            tip_w = tip.tip_window.winfo_reqwidth()
            tip_h = tip.tip_window.winfo_reqheight()
        return x, y, tip_w, tip_h


class TestT08aDefectProbes(_T08aTooltipTestBase):
    """Defect probes for T-08a (fail pre-patch with 0 errors, pass post-patch)."""

    def test_probe_1_right_edge_clamp(self) -> None:
        x, _y, tip_w, _tip_h = self._show_and_measure_tip(
            work_area=(0, 0, 1920, 1050),
            rootx=1800,
            rooty=100,
            height=20,
        )
        self.assertLessEqual(x + tip_w, 1918)
        self.assertGreaterEqual(x, 2)

    def test_probe_2_bottom_edge_flip(self) -> None:
        _x, y, _tip_w, tip_h = self._show_and_measure_tip(
            work_area=(0, 0, 1920, 1050),
            rootx=200,
            rooty=1020,
            height=25,
        )
        self.assertLess(y, 1020)
        self.assertLessEqual(y + tip_h, 1048)
        self.assertGreaterEqual(y, 2)

    def test_probe_3_left_edge_clamp(self) -> None:
        x, _y, _tip_w, _tip_h = self._show_and_measure_tip(
            work_area=(0, 0, 1920, 1050),
            rootx=-20,
            rooty=200,
            height=20,
        )
        self.assertGreaterEqual(x, 2)

    def test_probe_4_top_edge_clamp(self) -> None:
        _x, y, _tip_w, tip_h = self._show_and_measure_tip(
            work_area=(0, 0, 1920, 1050),
            rootx=200,
            rooty=-20,
            height=10,
        )
        self.assertGreaterEqual(y, 2)
        self.assertLessEqual(y + tip_h, 1048)

    def test_probe_5_multi_monitor_negative(self) -> None:
        x, _y, tip_w, _tip_h = self._show_and_measure_tip(
            work_area=(-1920, 0, 0, 1050),
            rootx=-100,
            rooty=100,
            height=20,
        )
        self.assertGreaterEqual(x, -1918)
        self.assertLessEqual(x + tip_w, -2)
        self.assertLess(x, 0)

    def test_probe_6_work_area_win32_prototypes_and_negative_monitor(self) -> None:
        fn = getattr(misora, "_get_work_area", None)
        self.assertIsNotNone(fn, "_get_work_area not implemented")
        from ctypes import wintypes as _wt

        captured: dict[str, object] = {}

        class _FakeMonitorFromPoint:
            argtypes = None
            restype = None

            def __call__(self, pt, flags):
                captured["pt"] = (pt.x, pt.y)
                captured["flags"] = flags
                return 0x1234

        class _FakeGetMonitorInfoW:
            argtypes = None
            restype = None

            def __call__(self, hmon, mi_ptr):
                captured["hmon"] = hmon
                mi = mi_ptr._obj
                mi.rcWork.left = -1920
                mi.rcWork.top = 0
                mi.rcWork.right = 0
                mi.rcWork.bottom = 1040
                return 1

        fake_user32 = mock.Mock()
        fake_user32.MonitorFromPoint = _FakeMonitorFromPoint()
        fake_user32.GetMonitorInfoW = _FakeGetMonitorInfoW()

        with mock.patch.object(misora.sys, "platform", "win32"), \
             mock.patch.object(misora.ctypes, "WinDLL", return_value=fake_user32) as windll_mock:
            result = fn(-500, 200)

        windll_mock.assert_called_once_with("user32", use_last_error=True)
        expected_hmon = getattr(_wt, "HMONITOR", _wt.HANDLE)
        self.assertEqual(fake_user32.MonitorFromPoint.argtypes, [_wt.POINT, _wt.DWORD])
        self.assertEqual(fake_user32.MonitorFromPoint.restype, expected_hmon)
        self.assertEqual(len(fake_user32.GetMonitorInfoW.argtypes), 2)
        self.assertEqual(fake_user32.GetMonitorInfoW.argtypes[0], expected_hmon)
        self.assertTrue(issubclass(fake_user32.GetMonitorInfoW.argtypes[1]._type_, ctypes.Structure))
        self.assertEqual(fake_user32.GetMonitorInfoW.restype, _wt.BOOL)
        self.assertEqual(captured["pt"], (-500, 200))
        self.assertEqual(captured["flags"], 2)
        self.assertEqual(captured["hmon"], 0x1234)
        self.assertEqual(result, (-1920, 0, 0, 1040))

    def test_probe_7_work_area_fallback_on_win32_failure_and_non_win32(self) -> None:
        fn = getattr(misora, "_get_work_area", None)
        self.assertIsNotNone(fn, "_get_work_area not implemented")

        fb = mock.Mock()
        fb.winfo_screenwidth.return_value = 1280
        fb.winfo_screenheight.return_value = 720

        # (a) MonitorFromPoint returns 0 -> fallback to widget screen size
        fake_u32_zero = mock.Mock()
        fake_u32_zero.MonitorFromPoint = mock.Mock(return_value=0)
        fake_u32_zero.GetMonitorInfoW = mock.Mock(return_value=1)
        with mock.patch.object(misora.sys, "platform", "win32"), \
             mock.patch.object(misora.ctypes, "WinDLL", return_value=fake_u32_zero):
            self.assertEqual(fn(10, 20, fallback_widget=fb), (0, 0, 1280, 720))

        # (b) GetMonitorInfoW returns 0 -> fallback to widget screen size
        fake_u32_fail = mock.Mock()
        fake_u32_fail.MonitorFromPoint = mock.Mock(return_value=0x1234)
        fake_u32_fail.GetMonitorInfoW = mock.Mock(return_value=0)
        with mock.patch.object(misora.sys, "platform", "win32"), \
             mock.patch.object(misora.ctypes, "WinDLL", return_value=fake_u32_fail):
            self.assertEqual(fn(10, 20, fallback_widget=fb), (0, 0, 1280, 720))

        # (c) WinDLL unavailable (OSError) -> fallback to widget screen size
        with mock.patch.object(misora.sys, "platform", "win32"), \
             mock.patch.object(misora.ctypes, "WinDLL", side_effect=OSError("user32 unavailable")):
            self.assertEqual(fn(10, 20, fallback_widget=fb), (0, 0, 1280, 720))

        # (d) Non-Windows platform -> fallback to widget screen size or (0, 0, 1920, 1080)
        with mock.patch.object(misora.sys, "platform", "linux"):
            self.assertEqual(fn(10, 20, fallback_widget=fb), (0, 0, 1280, 720))
            self.assertEqual(fn(10, 20, fallback_widget=None), (0, 0, 1920, 1080))

        # (e) Signature/argument errors must NOT be silently masked
        fake_u32_argerr = mock.Mock()
        fake_u32_argerr.MonitorFromPoint = mock.Mock(side_effect=ctypes.ArgumentError("bad arg"))
        fake_u32_argerr.GetMonitorInfoW = mock.Mock(return_value=1)
        with mock.patch.object(misora.sys, "platform", "win32"), \
             mock.patch.object(misora.ctypes, "WinDLL", return_value=fake_u32_argerr):
            with self.assertRaises(ctypes.ArgumentError):
                fn(10, 20, fallback_widget=fb)


class TestT08aRegressionGuards(_T08aTooltipTestBase):
    """Regression guards for T-08a (pass both pre-patch and post-patch)."""

    def test_guard_1_center_screen_standard_position(self) -> None:
        x, y, _tip_w, _tip_h = self._show_and_measure_tip(
            work_area=(0, 0, 1920, 1050),
            rootx=500,
            rooty=300,
            height=22,
        )
        self.assertEqual(x, 508)
        self.assertEqual(y, 326)

    def test_guard_2_tooltip_text_preserved(self) -> None:
        tip = self.app.lbl_char_overflow._tooltip.text
        self.assertIn(str(DIALOGUE_MAX_DIGITS), tip)
        self.assertIn(str(DIALOGUE_MAX_LINES), tip)
        self.assertIn("digit-widths", tip)
        self.assertIn("active editor font", tip)
        self.assertIn("fixed reference boundary", tip)

    def test_guard_3_hide_tip_destroys_cleanly(self) -> None:
        tip = self.app.lbl_char_overflow._tooltip
        tip.show_tip()
        self.assertIsNotNone(tip.tip_window)
        self.assertTrue(tip.tip_window.winfo_exists())
        tip.hide_tip()
        self.assertIsNone(tip.tip_window)


if __name__ == "__main__":
    unittest.main()
