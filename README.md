# Switch Typer

Type `bootstrap.bas` into a receiving editor using NetHunter's USB HID keyboard
device. The Python scripts use only the standard library.

## Bootstrap source

The included `bootstrap.bas` was obtained from
[kurumuz/ns2jb on GitLab](https://gitlab.com/kurumuz/ns2jb/).
Refer to that repository for the bootstrap's requirements and instructions before
running the BASIC program. This project's typing instructions only cover entering
the file into the editor.

## Requirements

- Python 3.
- For typing: NetHunter Kali with a working 8-byte USB HID keyboard device
  (default: `/dev/hidg0`), connected to the receiver. Run the typing command as root.
- The receiver's keyboard layout must match `--layout`: Spanish (Spain), `es`,
  or US English, `us`. The default is `es`.
- Turn off Caps Lock and auto-indent in the receiving editor.

HID sends key positions, so the receiver's layout matters. The sender's keyboard
layout does not. The character map covers the letters, digits, and punctuation
needed by the included bootstrap; it is not a general Unicode text typer.

## Usage

The setup used for this project is a rooted Android device with the Kali kernel
and Kali Full installed. A NetHunter custom command runs `type-bootstrap.sh`
inside Kali as root.

### Copy the files to the device

With USB debugging enabled and the computer authorized on the Android device,
run these commands from this repository on your computer (requires `adb`):

```bash
adb shell mkdir -p /sdcard/nh_files /sdcard/Download
adb push hid-type-file.py type-bootstrap.sh /sdcard/nh_files/
adb push bootstrap.bas /sdcard/Download/bootstrap.bas
```

These paths match the included launcher: `type-bootstrap.sh` runs
`/sdcard/nh_files/hid-type-file.py`, which reads
`/sdcard/Download/bootstrap.bas` by default. Repeat the relevant `adb push`
command whenever you update a file.

### Run inside Kali

Configure the NetHunter custom command to execute this in Kali as root:

```bash
sh /sdcard/nh_files/type-bootstrap.sh
```

You can also run that command directly in a root Kali terminal. The launcher
forwards arguments to Python. To validate the copied file without typing:

```bash
sh /sdcard/nh_files/type-bootstrap.sh --check
```

For a receiver using US English:

```bash
sh /sdcard/nh_files/type-bootstrap.sh --layout us
```

Focus an empty receiving editor during the five-second countdown. Press Ctrl+C
to stop. The script types the file; it does not run the BASIC program.

### Run Python directly

From this directory, validate the file without opening a HID device or typing:

```bash
python3 hid-type-file.py bootstrap.bas --check
```

Type the file from a root shell inside NetHunter Kali:

```bash
python3 hid-type-file.py bootstrap.bas --layout es
```

Available options:

| Option | Default | Purpose |
| --- | --- | --- |
| Positional file path | `/sdcard/Download/bootstrap.bas` | File to type |
| `--layout` | `es` | Receiver layout: `es` or `us` |
| `--device` | `/dev/hidg0` | HID keyboard device |
| `--character-ms` | `80` | Time per non-newline character, in milliseconds |
| `--newline-ms` | `250` | Time per newline, in milliseconds |
| `--countdown` | `5` | Seconds before typing starts |
| `--check` | Disabled | Validate characters and exit without typing |

Character and newline delays must be at least 40 ms; the countdown must be
nonnegative. Unsupported characters are rejected before typing starts.

## Regression test

Run on a normal computer without root or a HID device:

```bash
python3 -m unittest -v test_hid_type_file.py
```

The test runs the typing code with a simulated receiver. It independently decodes
the outgoing HID reports into a temporary text file, then compares that file with
`bootstrap.bas` byte for byte for both layouts. It also checks that keys are
released between characters and at completion. The temporary files are removed
after the test.

This verifies the generated reports and text, but does not test physical USB
delivery, the receiver's layout settings, or whether the editor keeps up with
the typing speed.
