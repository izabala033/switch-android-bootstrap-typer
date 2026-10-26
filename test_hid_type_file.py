"""Run with: python3 -m unittest -v test_hid_type_file.py"""

import importlib.util
import io
from pathlib import Path
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("hid_type_file", ROOT / "hid-type-file.py")
if spec is None or spec.loader is None:
    raise ImportError("Cannot load hid-type-file.py")
typer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(typer)

# Receiver-side key labels, independent of the sender's keyboard_map().
# Each pair is (unshifted, shifted), indexed by the USB HID usage code.
PUNCTUATION = {
    "us": {
        45: "-_", 46: "=+", 47: "[{", 48: "]}", 49: "\\|",
        51: ";:", 52: "'\"", 54: ",<", 55: ".>", 56: "/?",
    },
    "es": {
        45: "'?", 46: "¡¿", 48: "+*", 49: "çÇ", 51: "ñÑ",
        54: ",;", 55: ".:", 56: "-_", 100: "<>",
    },
}
SHIFTED_DIGITS = {"us": "!@#$%^&*()", "es": '!"·$%&/()='}
ALTGR_ES = {30: "|", 32: "#", 47: "[", 48: "]"}


class TextReceiver:
    """Decode key-down reports into a file, requiring release between keys."""

    def __init__(self, output, layout):
        self.output = output
        self.layout = layout
        self.pressed = False
        self.characters = 0

    def write(self, fd, data):
        if fd != 123 or len(data) != 8 or data[1] or any(data[3:]):
            raise AssertionError(f"Invalid keyboard report: {data!r}")
        if data == bytes(8):
            self.pressed = False
            return 8
        if self.pressed:
            raise AssertionError("Missing key release")
        modifier, key = data[0], data[2]
        if modifier == 64 and self.layout == "es":
            char = ALTGR_ES[key]
        elif modifier in (0, 2):
            shifted = modifier == 2
            if 4 <= key <= 29:
                char = chr((ord("A") if shifted else ord("a")) + key - 4)
            elif 30 <= key <= 39:
                labels = SHIFTED_DIGITS[self.layout] if shifted else "1234567890"
                char = labels[key - 30]
            elif key in (40, 44) and not shifted:
                char = {40: "\n", 44: " "}[key]
            else:
                char = PUNCTUATION[self.layout][key][shifted]
        else:
            raise AssertionError(f"Unexpected modifier: {modifier}")
        self.output.write(char)
        self.characters += 1
        self.pressed = True
        return 8


class BootstrapTypingTest(unittest.TestCase):
    def test_bootstrap_round_trip(self):
        source = ROOT / "bootstrap.bas"
        for layout in ("es", "us"):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as directory:
                destination = Path(directory) / "received.bas"
                with destination.open("w", encoding="utf-8", newline="") as output:
                    receiver = TextReceiver(output, layout)
                    # Replace only the device boundary; main(), report(), and
                    # write_report() still run normally. No real HID is opened.
                    device = SimpleNamespace(
                        O_WRONLY=typer.os.O_WRONLY,
                        O_NONBLOCK=typer.os.O_NONBLOCK,
                        stat=Mock(return_value=SimpleNamespace(st_mode=stat.S_IFCHR)),
                        open=Mock(return_value=123),
                        write=Mock(side_effect=receiver.write),
                        close=Mock(),
                    )
                    argv = ["hid-type-file.py", str(source), "--layout", layout,
                            "--device", "/fake/hid", "--countdown", "0"]
                    with patch.object(typer, "os", device), \
                            patch.object(typer.sys, "argv", argv), \
                            patch.object(typer.time, "sleep"), redirect_stdout(io.StringIO()):
                        typer.main()
                    device.open.assert_called_once_with(
                        "/fake/hid", device.O_WRONLY | device.O_NONBLOCK
                    )
                    device.close.assert_called_once_with(123)
                    self.assertFalse(receiver.pressed, "A key was left held down")
                    self.assertGreater(receiver.characters, 0)
                self.assertEqual(destination.read_bytes(), source.read_bytes())


if __name__ == "__main__":
    unittest.main()
