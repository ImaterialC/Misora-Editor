import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import misora
from misora import DIALOGUE_MAX_DIGITS, DIALOGUE_MAX_LINES, MisoraApp


class _T02TooltipTestBase(unittest.TestCase):
    """Shared MisoraApp harness for T-02 tooltip probes and guards."""

    def setUp(self) -> None:
        self._orig_config_path = misora.CONFIG_PATH
        self.temp_dir = Path(tempfile.mkdtemp(prefix="misora_t02_"))
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
                    self.app.destroy()
                except Exception:
                    pass
        finally:
            misora.CONFIG_PATH = self._orig_config_path
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestT02DefectProbes(_T02TooltipTestBase):
    """Defect probes for T-02 (fail pre-patch, pass post-patch)."""

    def test_probe_1_overflow_tooltip_uses_54d_and_dual_font_wording(self) -> None:
        tip = self.app.lbl_char_overflow._tooltip.text
        self.assertIn(str(DIALOGUE_MAX_DIGITS), tip)
        self.assertNotIn("50 x 3", tip)
        self.assertNotIn("50 digit-widths", tip)
        self.assertIn("active editor font", tip)
        self.assertIn("fixed reference boundary", tip)

    def test_probe_2_update_char_overflow_indicator_docstring(self) -> None:
        doc = self.app._update_char_overflow_indicator.__doc__ or ""
        self.assertIn("54d", doc)
        self.assertNotIn("50d", doc)

    def test_probe_3_get_ruler_measure_font_docstring(self) -> None:
        doc = self.app._get_ruler_measure_font.__doc__ or ""
        self.assertIn("54d", doc)
        self.assertNotIn("50d", doc)

    def test_probe_4_draw_single_pixel_ruler_docstring(self) -> None:
        doc = self.app._draw_single_pixel_ruler.__doc__ or ""
        self.assertIn("54 digit-width", doc)
        self.assertNotIn("50 digit-width", doc)


class TestT02RegressionGuards(_T02TooltipTestBase):
    """Regression guards for T-02 (pass both pre-patch and post-patch)."""

    def test_guard_1_dialogue_max_constants(self) -> None:
        self.assertEqual(DIALOGUE_MAX_DIGITS, 54)
        self.assertEqual(DIALOGUE_MAX_LINES, 3)

    def test_guard_2_overflow_label_initial_text_is_dynamic(self) -> None:
        expected = f"0/{DIALOGUE_MAX_DIGITS}d · 1/{DIALOGUE_MAX_LINES}L"
        self.assertEqual(expected, "0/54d · 1/3L")
        self.assertEqual(self.app.lbl_char_overflow.cget("text"), expected)

    def test_guard_3_btn_next_tooltip_unchanged(self) -> None:
        self.assertEqual(
            self.app.btn_next._tooltip.text,
            "Next Dialogue Box (Alt+Right / Alt+Down)",
        )

    def test_guard_4_btn_prev_tooltip_unchanged(self) -> None:
        self.assertEqual(
            self.app.btn_prev._tooltip.text,
            "Previous Dialogue Box (Alt+Left / Alt+Up)",
        )


if __name__ == "__main__":
    unittest.main()
