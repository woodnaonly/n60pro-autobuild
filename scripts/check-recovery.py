#!/usr/bin/env python3
"""Fail closed on unexpected packages, invalid FITs or oversized recovery data."""

import argparse
import hashlib
import json
import lzma
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess
import tempfile
import zlib


MIB = 1024 * 1024
MAX_FIT = 16 * MIB
MAX_CPIO = 64 * MIB
MAX_KERNEL = 32 * MIB
TFTP_LOAD = 0x46000000
KERNEL_LOAD = 0x48000000
DRAM_START = 0x40000000
DRAM_SIZE = 512 * MIB
DEVICE = "netcore,n60-pro"
OVERLAY = Path(__file__).resolve().parent.parent / "recovery-overlay"
REQUIRED_PACKAGES = {
    "base-files", "busybox", "dnsmasq", "dropbear", "fitblk", "fit-check-sign",
    "fstools", "fwtool", "logd", "mtd", "nand-utils", "netifd", "procd", "ubus",
    "ubi-utils", "uci", "kmod-gpio-button-hotplug", "kmod-leds-gpio",
}
ALLOWED_PACKAGES = REQUIRED_PACKAGES | {
    "ca-bundle", "getrandom", "jshn", "jsonfilter", "kernel", "libc", "libgcc",
    "openwrt-keyring", "procd-seccomp", "ubox", "ubusd", "ucert", "ucert-full", "ucode",
    "uclient-fetch", "urandom-seed", "urngd", "usign",
}
BUILD_ONLY = {
    "u-boot-mt7986_netcore_n60-pro",
    "trusted-firmware-a-mt7986-spim-nand-ddr4",
}
REQUIRED_FILES = {
    "init", "bin/busybox", "etc/preinit", "etc/shadow",
    "etc/init.d/dropbear", "etc/init.d/dnsmasq",
    "sbin/netifd", "sbin/procd", "sbin/sysupgrade", "sbin/mtd",
    "usr/sbin/dropbear", "usr/sbin/dnsmasq", "usr/sbin/fitblk",
    "usr/bin/fit_check_sign", "usr/bin/fwtool", "usr/sbin/ubinfo", "usr/sbin/ubiattach",
    "usr/sbin/ubiformat", "usr/sbin/ubiupdatevol", "usr/sbin/nanddump",
    "lib/upgrade/fit.sh", "lib/upgrade/nand.sh", "lib/upgrade/platform.sh",
}
PARTITIONS = {
    "bl2": (0x0, 0x100000),
    "u-boot-env": (0x100000, 0x80000),
    "factory": (0x180000, 0x200000),
    "fip": (0x380000, 0x200000),
    "ubi": (0x580000, 0x7A80000),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_config(path):
    values = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"(CONFIG_[\w-]+)=(.*)", line)
        disabled = re.fullmatch(r"# (CONFIG_[\w-]+) is not set", line)
        if match:
            key, value = match.groups()
        elif disabled:
            key, value = disabled.group(1), "n"
        else:
            continue
        require(key not in values, f"Duplicate config entry: {key}")
        values[key] = value
    return values


def check_packages(packages):
    packages = set(packages)
    missing = REQUIRED_PACKAGES - packages
    unexpected = {
        name for name in packages
        if name not in ALLOWED_PACKAGES
        and not name.startswith(("lib", "ucode-mod-"))
    }
    require(not missing, f"Missing recovery packages: {sorted(missing)}")
    require(not unexpected, f"Unexpected recovery packages: {sorted(unexpected)}")
    return sorted(packages)


def check_config(values):
    for key in (
        "CONFIG_TARGET_mediatek", "CONFIG_TARGET_mediatek_filogic",
        "CONFIG_TARGET_MULTI_PROFILE",
        "CONFIG_TARGET_DEVICE_mediatek_filogic_DEVICE_netcore_n60-pro",
        "CONFIG_TARGET_PER_DEVICE_ROOTFS", "CONFIG_TARGET_ROOTFS_INITRAMFS",
        "CONFIG_TARGET_ROOTFS_INITRAMFS_SEPARATE",
        "CONFIG_TARGET_INITRAMFS_COMPRESSION_XZ",
    ):
        require(values.get(key) == "y", f"Required setting missing: {key}=y")
    devices = [
        key for key, value in values.items()
        if key.startswith("CONFIG_TARGET_DEVICE_")
        and "_DEVICE_" in key and value == "y"
    ]
    require(len(devices) == 1, "Recovery must select exactly one device")
    for key in (
        "CONFIG_ALL", "CONFIG_ALL_KMODS", "CONFIG_ALL_NONSHARED",
        "CONFIG_BUILDBOT", "CONFIG_TARGET_INITRAMFS_FORCE",
        "CONFIG_KERNEL_DEBUG_INFO_BTF", "CONFIG_KERNEL_XDP_SOCKETS",
        "CONFIG_TARGET_ROOTFS_SQUASHFS", "CONFIG_TARGET_ROOTFS_EROFS",
    ):
        require(values.get(key, "n") == "n", f"Unexpected recovery setting: {key}")
    packages = [
        key.removeprefix("CONFIG_PACKAGE_")
        for key, value in values.items()
        if key.startswith("CONFIG_PACKAGE_") and value == "y"
    ]
    for name in BUILD_ONLY:
        # Kconfig declares boot artifacts as bool, so they can only be '=y'; they
        # stage into the image directory and must never reach the rootfs checks.
        require(values.get(f"CONFIG_PACKAGE_{name}") == "y",
                f"Boot artifact must be selected for build: {name}=y")
    return check_packages(set(packages) - BUILD_ONLY)


def check_kernel_config(values):
    for name in (
        "BLK_DEV_INITRD", "RD_XZ", "NET_MEDIATEK_SOC", "NET_DSA_MT7530",
        "MAXLINEAR_GPHY", "MTD_SPI_NAND", "MTD_UBI",
    ):
        require(values.get(f"CONFIG_{name}") == "y",
                f"Required built-in kernel support missing: {name}")
    for name in ("MT_WIFI", "MTK_MT_WIFI", "MT76_CORE", "MT7915E", "MAC80211"):
        require(values.get(f"CONFIG_{name}", "n") == "n",
                f"Unexpected wireless kernel support: {name}")


def run_tool(args, data=None):
    result = subprocess.run(args, input=data, capture_output=True, timeout=120)
    require(result.returncode == 0,
            f"{args[0]} failed: {result.stderr.decode('utf-8', 'replace')[:1500]}")
    return result.stdout


def fdt(path, node, prop=None, kind="s"):
    args = ["fdtget"]
    args += ["-l"] if prop is None else ["-t", kind]
    args += [str(path), node]
    if prop is not None:
        args.append(prop)
    return run_tool(args).decode("utf-8").strip().split()


def fdt_number(path, node, prop):
    cells = fdt(path, node, prop, "x")
    require(len(cells) in (1, 2), f"Invalid FIT address: {node}/{prop}")
    value = 0
    for cell in cells:
        value = (value << 32) | int(cell, 16)
    return value


def check_hashes(image, node, payload):
    hashes = fdt(image, node)
    algorithms = set()
    for child in hashes:
        require(child.startswith("hash"), f"Unexpected FIT image child: {child}")
        path = f"{node}/{child}"
        algo = fdt(image, path, "algo")[0]
        expected = bytes(int(cell, 16) for cell in fdt(image, path, "value", "bx"))
        if algo == "crc32":
            actual = struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)
        elif algo in ("sha1", "sha256"):
            actual = hashlib.new(algo, payload).digest()
        else:
            raise ValueError(f"Unsupported FIT hash: {algo}")
        require(expected == actual, f"FIT hash mismatch: {node}/{algo}")
        algorithms.add(algo)
    require({"crc32", "sha1"} <= algorithms, f"Missing FIT hashes: {node}")


def decompress(payload, fmt, maximum):
    decoder = lzma.LZMADecompressor(format=fmt, memlimit=128 * MIB)
    unpacked = decoder.decompress(payload, max_length=maximum + 1)
    require(len(unpacked) <= maximum, f"Decompressed data exceeds {maximum} bytes")
    require(decoder.eof and not decoder.unused_data,
            "Incomplete or trailing compressed data")
    return unpacked


def check_layout(fit_size, kernel_size, load=TFTP_LOAD):
    require(fit_size <= MAX_FIT, "FIT exceeds the 16 MiB project limit")
    require(kernel_size <= MAX_KERNEL, "Kernel exceeds the 32 MiB project limit")
    require(DRAM_START <= load < load + fit_size <= KERNEL_LOAD,
            "FIT source overlaps the kernel load address or is outside DRAM")
    require(KERNEL_LOAD + kernel_size <= DRAM_START + DRAM_SIZE,
            "Decompressed kernel is outside DRAM")


def check_device_tree(path):
    require(DEVICE in fdt(path, "/", "compatible"), "Wrong recovery device tree")
    memory = [int(cell, 16) for cell in fdt(path, "/memory@40000000", "reg", "x")]
    require(memory == [0, DRAM_START, 0, DRAM_SIZE], "Unexpected DRAM layout")
    pending = ["/"]
    partitions = {}
    while pending:
        node = pending.pop()
        children = fdt(path, node)
        if PurePosixPath(node).name == "partitions":
            for child in children:
                part = f"{node}/{child}"
                label = fdt(path, part, "label")[0]
                reg = tuple(int(cell, 16) for cell in fdt(path, part, "reg", "x"))
                require(label not in partitions, f"Duplicate partition: {label}")
                partitions[label] = reg
        else:
            pending.extend(
                f"{node.rstrip('/')}/{child}" for child in children
            )
    require(partitions == PARTITIONS, f"Unexpected NAND layout: {partitions}")


def check_archive_names(names):
    names = {name.removeprefix("./") for name in names}
    for name in names:
        path = PurePosixPath(name)
        require(not path.is_absolute() and ".." not in path.parts,
                f"Unsafe archive path: {name}")
        require(name == path.as_posix(), f"Noncanonical archive path: {name}")
        require(not name.startswith((
            "usr/share/luci/", "usr/lib/lua/luci/", "usr/share/v2ray/",
            "usr/share/honk/", "etc/Wireless/", "lib/firmware/mediatek/",
        )), f"Unexpected wireless/plugin files: {name}")
        require(not any(word in path.name.lower() for word in (
            "honk", "netspeed", "geoip", "geosite", "mt_wifi", "mt7915",
            "mt76", "mac80211", "cfg80211", "conninfra", "warp.ko",
        )), f"Unexpected wireless/plugin file: {name}")
        require(name not in (
            "etc/uci-defaults/98-lan-ip", "etc/uci-defaults/99-default-wifi",
        ), f"Normal firmware overlay leaked into recovery: {name}")
    missing = REQUIRED_FILES - names
    require(not missing, f"Missing recovery files: {sorted(missing)}")
    return names


def archive_file(cpio, names, name):
    require(name in names, f"Missing recovery configuration: {name}")
    return run_tool(
        ["cpio", "-i", "--quiet", "--to-stdout", names[name]], cpio
    )


def check_archive(cpio):
    original = run_tool(["cpio", "-it", "--quiet"], cpio).decode("utf-8").splitlines()
    checked = check_archive_names(original)
    names = {name.removeprefix("./"): name for name in original}
    require(len(checked) == len(original), "Duplicate paths in recovery archive")
    for file in sorted(OVERLAY.rglob("*")):
        if file.is_file():
            name = file.relative_to(OVERLAY).as_posix()
            require(archive_file(cpio, names, name) == file.read_bytes(),
                    f"Recovery overlay mismatch: {name}")
    shadow = archive_file(cpio, names, "etc/shadow").decode("utf-8")
    root = [line.split(":") for line in shadow.splitlines() if line.startswith("root:")]
    require(len(root) == 1 and root[0][1].startswith("$6$"),
            "Recovery root password must have a SHA-512 crypt hash")
    return len(names)


def read_manifest(path):
    packages = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        name, sep, version = line.partition(" - ")
        require(sep and name and version, f"Invalid package manifest line: {line}")
        packages.append(name)
    return check_packages(packages)


def check_image(image, kernel_config, manifest):
    image = Path(image)
    require(image.stat().st_size <= MAX_FIT, "FIT exceeds the 16 MiB project limit")
    check_kernel_config(read_config(kernel_config))
    packages = read_manifest(manifest)
    require(fdt(image, "/configurations", "default") == ["config-1"],
            "FIT default configuration must be config-1")
    refs = {
        "kernel": "kernel-1", "ramdisk": "initrd-1", "fdt": "fdt-1",
    }
    for prop, name in refs.items():
        require(fdt(image, "/configurations/config-1", prop) == [name],
                f"Unexpected FIT configuration reference: {prop}")
    images = fdt(image, "/images")
    require(set(images) == set(refs.values()) and len(images) == 3,
            "Unexpected FIT subimages")
    with tempfile.TemporaryDirectory() as directory:
        payloads = {}
        for name, kind in (
            ("kernel-1", "kernel"), ("initrd-1", "ramdisk"), ("fdt-1", "flat_dt"),
        ):
            node = f"/images/{name}"
            require(fdt(image, node, "type") == [kind], f"Wrong FIT type: {name}")
            require(fdt(image, node, "arch") == ["arm64"], f"Wrong FIT arch: {name}")
            if kind != "flat_dt":
                require(fdt(image, node, "os") == ["linux"], f"Wrong FIT OS: {name}")
            output = Path(directory) / name
            run_tool([
                "dumpimage", "-T", "flat_dt", "-p", str(images.index(name)),
                "-o", str(output), str(image),
            ])
            payloads[name] = output.read_bytes()
            check_hashes(image, node, payloads[name])
        require(fdt(image, "/images/kernel-1", "compression") == ["lzma"],
                "Recovery kernel must use LZMA")
        require(fdt(image, "/images/fdt-1", "compression") == ["none"],
                "Recovery device tree must be uncompressed")
        for prop in ("load", "entry"):
            require(fdt_number(image, "/images/kernel-1", prop) == KERNEL_LOAD,
                    f"Unexpected kernel {prop} address")
        kernel = decompress(payloads["kernel-1"], lzma.FORMAT_ALONE, MAX_KERNEL)
        require(len(kernel) >= 64 and kernel[56:60] == b"ARM\x64",
                "Invalid ARM64 kernel header")
        extent = max(len(kernel), struct.unpack_from("<Q", kernel, 16)[0])
        check_layout(image.stat().st_size, extent)
        check_device_tree(Path(directory) / "fdt-1")
        cpio = decompress(payloads["initrd-1"], lzma.FORMAT_XZ, MAX_CPIO)
        entries = check_archive(cpio)
    return {
        "image": image.name, "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "fit_bytes": image.stat().st_size, "kernel_bytes": len(kernel),
        "kernel_memory_extent": extent, "initramfs_xz_bytes": len(payloads["initrd-1"]),
        "initramfs_cpio_bytes": len(cpio), "archive_entries": entries,
        "packages": packages, "assumed_tftp_load": hex(TFTP_LOAD),
        "kernel_load": hex(KERNEL_LOAD),
        "limits": {"fit": MAX_FIT, "cpio": MAX_CPIO, "kernel": MAX_KERNEL},
        "hardware_boot_verified": False,
        "notes": [
            "Static checks do not verify U-Boot ramdisk relocation or runtime memory.",
            "Limits are project policy, not hardware or U-Boot limits.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    config = commands.add_parser("config")
    config.add_argument("path", type=Path)
    image = commands.add_parser("image")
    image.add_argument("path", type=Path)
    image.add_argument("--kernel-config", type=Path, required=True)
    image.add_argument("--manifest", type=Path, required=True)
    image.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "config":
            packages = check_config(read_config(args.path))
            print(f"Recovery config passed: {len(packages)} installed packages")
        else:
            report = check_image(args.path, args.kernel_config, args.manifest)
            args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(f"Recovery checks passed: FIT={report['fit_bytes']} bytes, "
                  f"CPIO={report['initramfs_cpio_bytes']} bytes")
    except (ValueError, OSError, lzma.LZMAError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"::error::{error}\n")


if __name__ == "__main__":
    main()
