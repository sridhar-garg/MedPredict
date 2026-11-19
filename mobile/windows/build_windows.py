#!/usr/bin/env python3
"""Compile the MedPredict Windows launcher using Zig's Windows cross toolchain."""
import argparse
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent


def make_icon(destination):
    # Same medical box, cross and checkmark proportions as the sidebar mark.
    scale = 8
    image = Image.new("RGBA", (64 * scale, 64 * scale))
    draw = ImageDraw.Draw(image)

    def box(coordinates):
        return tuple(round(value * scale) for value in coordinates)

    def rounded(coordinates, radius, **kwargs):
        draw.rounded_rectangle(box(coordinates), radius=radius * scale, **kwargs)

    def stroke(points, color, width):
        scaled = [box(point) for point in points]
        draw.line(scaled, fill=color, width=round(width * scale), joint="curve")
        radius = width / 2
        for x, y in points:
            draw.ellipse(box((x - radius, y - radius, x + radius, y + radius)), fill=color)

    rounded((0, 0, 63.9, 63.9), 17, fill="#096961")
    rounded((23, 10, 41, 26), 4, outline="#E1F2EE", width=4 * scale)
    rounded((9, 19, 55, 55), 10, fill="#FFFFFF")
    stroke([(32, 27), (32, 47)], "#096961", 5)
    stroke([(22, 37), (42, 37)], "#096961", 5)
    draw.ellipse(box((41, 14, 57, 30)), fill="#7EE5CC")
    stroke([(45, 22), (48, 25), (53, 19)], "#194D44", 2.5)
    image.save(destination, sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig", type=Path, required=True, help="Path to the Zig executable")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    zig = str(args.zig.resolve())
    output = args.out.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="medpredict-windows-") as build:
        work = Path(build)
        for filename in ("MedPredict.c", "MedPredict.rc", "MedPredict.manifest"):
            shutil.copyfile(ROOT / filename, work / filename)
        make_icon(work / "MedPredict.ico")
        subprocess.run([zig, "rc", "/fo", "MedPredict.res", "MedPredict.rc"], cwd=work, check=True)
        subprocess.run([
            zig, "cc", "-target", "x86_64-windows-gnu", "-O2", "-s",
            "-municode", "-Wl,--subsystem,windows", "MedPredict.c", "MedPredict.res",
            "-lole32", "-lshell32", "-luuid", "-ladvapi32", "-luser32", "-o", str(output),
        ], cwd=work, check=True)
    print("Windows application:", output)


if __name__ == "__main__":
    main()
