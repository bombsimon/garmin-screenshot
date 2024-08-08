from pathlib import Path

import pytest

from garmin_screenshot import garmin_screenshot


@pytest.fixture()
def manifest():
    manifest = Path("manifest.xml")
    manifest.write_text("""<?xml version="1.0"?>
<iq:manifest version="3" xmlns:iq="http://www.garmin.com/xml/connectiq">
    <iq:application id="0531c950-69a4-4693-a328-f926ba20427e"
            type="watchface"
            name="@Strings.AppName"
            entry="SomeApp">
        <iq:products>
            <iq:product id="approachs60"/>
            <iq:product id="approachs62"/>
            <iq:product id="epix2"/>
            <iq:product id="fr255"/>
            <iq:product id="venu2"/>
        </iq:products>
        <iq:permissions/>
        <iq:languages/>
        <iq:barrels/>
    </iq:application>
</iq:manifest>""")

    yield manifest

    manifest.unlink()


def test_get_device(manifest: Path):  # noqa: ARG001 - Needed for fixture
    assert garmin_screenshot.get_devices(Path()) == [
        "approachs60",
        "approachs62",
        "epix2",
        "fr255",
        "venu2",
    ]
