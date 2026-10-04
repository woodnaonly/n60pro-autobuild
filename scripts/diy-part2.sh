#!/bin/bash
# 注册 512MB ROM 变体 (ubi=490MB 吃满, 对应 WildEdition uboot 的 506.5MB 分区表)
if ! grep -q 'define Device/netcore_n60-pro-512rom' target/linux/mediatek/image/filogic.mk; then
cat >> target/linux/mediatek/image/filogic.mk <<'MK'

define Device/netcore_n60-pro-512rom
  DEVICE_VENDOR := Netcore
  DEVICE_MODEL := N60 Pro (512MB ROM)
  DEVICE_DTS := mt7986a-netcore-n60-pro-512rom
  DEVICE_DTS_DIR := ../dts
  UBINIZE_OPTS := -E 5
  BLOCKSIZE := 128k
  PAGESIZE := 2048
  KERNEL_IN_UBI := 1
  UBOOTENV_IN_UBI := 1
  IMAGES := sysupgrade.itb
  KERNEL_INITRAMFS_SUFFIX := -recovery.itb
  KERNEL := kernel-bin | gzip
  KERNEL_INITRAMFS := kernel-bin | lzma | \
	fit lzma $$(KDIR)/image-$$(firstword $$(DEVICE_DTS)).dtb with-initrd | pad-to 64k
  IMAGE/sysupgrade.itb := append-kernel | \
	fit gzip $$(KDIR)/image-$$(firstword $$(DEVICE_DTS)).dtb external-static-with-rootfs | append-metadata
  DEVICE_PACKAGES := kmod-usb3 kmod-usb-storage kmod-usb-storage-uas automount autocore kmod-usb-storage-extras
  ARTIFACTS := preloader.bin bl31-uboot.fip
  ARTIFACT/preloader.bin := mt7986-bl2 spim-nand-ddr4
  ARTIFACT/bl31-uboot.fip := mt7986-bl31-uboot netcore_n60-pro
endef
TARGET_DEVICES += netcore_n60-pro-512rom
MK
fi

# 1. 允许 512rom 复用 u-boot-mt7986_netcore_n60-pro 构建规则
if ! grep -q 'BUILD_DEVICES:=.*netcore_n60-pro-512rom' package/boot/uboot-mediatek/Makefile; then
  sed -i 's/BUILD_DEVICES:=netcore_n60-pro$/BUILD_DEVICES:=netcore_n60-pro netcore_n60-pro-512rom/' package/boot/uboot-mediatek/Makefile
fi

# 2. 补充 base-files 板卡与 LED、网络、sysupgrade 匹配
if ! grep -q 'netcore,n60-pro-512rom' target/linux/mediatek/filogic/base-files/etc/board.d/01_leds; then
  sed -i '/netcore,n60-pro|/a \\tnetcore,n60-pro-512rom|\\' target/linux/mediatek/filogic/base-files/etc/board.d/01_leds
fi

if ! grep -q 'netcore,n60-pro-512rom' target/linux/mediatek/filogic/base-files/etc/board.d/02_network; then
  sed -i '/netcore,n60-pro|/a \\tnetcore,n60-pro-512rom|\\' target/linux/mediatek/filogic/base-files/etc/board.d/02_network
fi

if ! grep -q 'netcore,n60-pro-512rom' target/linux/mediatek/filogic/base-files/lib/upgrade/platform.sh; then
  sed -i '/netcore,n60-pro|/a \\tnetcore,n60-pro-512rom|\\' target/linux/mediatek/filogic/base-files/lib/upgrade/platform.sh
fi

echo "=== 512rom profile registered ==="
grep -c 'netcore_n60-pro-512rom' target/linux/mediatek/image/filogic.mk
