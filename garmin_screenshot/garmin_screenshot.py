import argparse
import shutil
import subprocess
import time
from pathlib import Path
from xml.etree import ElementTree

import pyautogui
import pygetwindow


def get_devices(app_path: Path) -> list[str]:
    """Get all devices.

    Look at the products in the `manifest.xml` and get all supported products.

    :param app_path: Path to Garmin app
    :returns: List of all supported devices
    """
    tree = ElementTree.parse(app_path / "manifest.xml")
    root = tree.getroot()
    namespaces = {"iq": "http://www.garmin.com/xml/connectiq"}

    product_elements = root.findall(".//iq:product", namespaces)

    return [
        product_id for product in product_elements if (product_id := product.get("id"))
    ]


def start_simulator(sdk_path: Path) -> None:
    """Start the simulator.

    Ensure the simulator is started so we can load our applications.

    :param sdk_path: Path to the Garmin SDK. This should _exclude_ the `bin`
        directory and only contain the path up until
        `[...]/Sdks/connectiq-sdk-xxx`.
    """
    print("Starting simulator...")

    simulator = str(sdk_path / "bin" / "simulator")

    result = subprocess.Popen(
        [simulator],
        shell=False,
    )

    if result.returncode:
        raise RuntimeError(
            f"failed to run simulator, stdout={result.stdout}, stderr={result.stderr}"
        )


def build_and_load(
    device: str,
    sdk_path: Path,
    dev_key_path: Path,
    app_path: Path,
    prg_path: Path,
) -> None:
    """Build and load the app.

    Build and load the app for the specified device.

    :param device: Garmin name of devices, e.g. `fr965`
    :param sdk_path: Path to the Garmin SDK. This should _exclude_ the `bin`
        directory and only contain the path up until
        `[...]/Sdks/connectiq-sdk-xxx`
    :param dev_key_path: Path to your developer key in `.der` format
    :param app_path: Path to the Garmin application
    :param prg_path: Path to where to write your compiled application
    """
    app = str(prg_path / "app.prg")
    monkeyc = str(sdk_path / "bin" / "monkeyc")
    monkeydo = str(sdk_path / "bin" / "monkeydo")
    jungle_file = str(app_path / "monkey.jungle")

    monkeyc_result = subprocess.run(
        [
            monkeyc,
            "-d",
            device,
            "-f",
            jungle_file,
            "-o",
            app,
            "-y",
            dev_key_path,
        ],
        capture_output=True,
        check=False,
        shell=True,
    )

    if monkeyc_result.returncode:
        raise RuntimeError(
            f"failed to run monkeyc, stdout={monkeyc_result.stdout.decode()}, "
            f"stderr={monkeyc_result.stderr.decode()}"
        )

    monkeydo_result = subprocess.Popen(
        [
            monkeydo,
            app,
            device,
        ],
        shell=True,
    )

    if monkeydo_result.returncode:
        raise RuntimeError(
            "failed to run monkeydo, stdout={result.stdout}, stderr={result.stderr}"
        )


def screenshot(filename: Path, wait_for_focus: bool = False) -> None:
    """Take a screenshot.

    Focus on the simulator (or whatever app has the title `CIQ Simulator`, take
    a screenshot and save it to `filename`.

    :param filename: The file (path and name) to save the screenshot as
    """
    windows = [w for w in pygetwindow.getAllWindows() if "CIQ Simulator" in w.title]
    if len(windows) == 0:
        raise RuntimeError("Didn't find a window with the title 'CIQ Simulator'")

    window = windows[0]
    window.activate()

    if wait_for_focus:
        # Small delay to ensure the window is focused.
        # Only needed first time
        time.sleep(1)

    left, top, right, bottom = window.left, window.top, window.right, window.bottom
    width, height = right - left, bottom - top

    screenshot = pyautogui.screenshot(region=(left, top, width, height))

    screenshot.save(filename)
    print(f"Screenshot saved as {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Garmin Screenshotter",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--wait-time",
        type=int,
        default=5,
        help="Time to wait between launching and taking screenshot",
    )
    parser.add_argument(
        "--sdk-path",
        required=True,
        type=Path,
        help="Path to where your Garmin SDK is installed (excluding /bin)",
    )
    parser.add_argument(
        "--dev-key-path",
        required=True,
        type=Path,
        help="Path to your developer key (.der)",
    )
    parser.add_argument(
        "--garmin-app-path",
        required=True,
        type=Path,
        help="Path to your garmin app (needed for manifest.xml and monkey.jungle)",
    )
    parser.add_argument(
        "--output",
        default="screenshots",
        type=Path,
        help="Output director of where to put screenshots",
    )

    args = parser.parse_args()

    if not args.output.exists():
        args.output.mkdir(parents=True, exist_ok=True)

    prg_output = Path("__prg")
    if not prg_output.exists():
        prg_output.mkdir(parents=True, exist_ok=True)

    start_simulator(args.sdk_path)
    time.sleep(args.wait_time)

    wait_for_focus = True

    for device in get_devices(args.garmin_app_path):
        build_and_load(
            device,
            args.sdk_path,
            args.dev_key_path,
            args.garmin_app_path,
            prg_output,
        )
        time.sleep(args.wait_time)  # Arbitrary sleep in hope of app is loaded.

        filename = args.output / f"screenshot-{device}.png"
        screenshot(filename, wait_for_focus)

        wait_for_focus = False

    shutil.rmtree(prg_output)
