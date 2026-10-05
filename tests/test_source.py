import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "src" / "htix-touchpad.py"
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def assigned_number(name):
    for node in TREE.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError(f"Missing assignment for {name}")


class SourceTests(unittest.TestCase):
    def test_script_parses(self):
        self.assertIsInstance(TREE, ast.Module)

    def test_detects_multitouch_interface_by_capabilities(self):
        for symbol in (
            "ABS_MT_SLOT",
            "ABS_MT_POSITION_X",
            "ABS_MT_POSITION_Y",
            "ABS_MT_TRACKING_ID",
        ):
            self.assertIn(symbol, SOURCE)
        self.assertIn("REQUIRED_ABS_CODES.issubset(abs_codes)", SOURCE)

    def test_virtual_mouse_advertises_three_buttons(self):
        self.assertIn("e.BTN_LEFT", SOURCE)
        self.assertIn("e.BTN_RIGHT", SOURCE)
        self.assertIn("e.BTN_MIDDLE", SOURCE)
        self.assertIn("gesture_fingers == 3", SOURCE)

    def test_hold_is_deliberate(self):
        self.assertGreaterEqual(assigned_number("HOLD_TIME"), 0.9)
        self.assertIn("gesture_total_move + pending_move < HOLD_DISTANCE", SOURCE)

    def test_cursor_jump_guard_is_enabled(self):
        self.assertGreater(assigned_number("MAX_POINTER_DELTA"), 0)
        self.assertIn("count != previous_finger_count", SOURCE)
        self.assertIn("motion_x.clear()", SOURCE)
        self.assertIn("motion_y.clear()", SOURCE)


if __name__ == "__main__":
    unittest.main()
