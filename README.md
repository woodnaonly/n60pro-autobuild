# N60 Pro 自动编译固件

磊科 N60 Pro (MT7986A) 专用在线编译模板，产物自动发布到 [Releases](../../releases)。

## 固件特性

- 源码: [chasey-dev/immortalwrt-mt798x-rebase](https://github.com/chasey-dev/immortalwrt-mt798x-rebase) `25.12` 分支（MTK 原厂有线/无线驱动 + HNAT）
- USB 存储支持（USB 3.0、UAS、automount；与当前路由器包配置一致）
- 不包含 USB 蜂窝模组驱动或拨号工具
- MTK HNAT 硬件加速（`luci-app-turboacc-mtk`）
- honk 透明代理：LuCI 界面、配置和服务脚本来自 189160/luci-app-honk，内核开启 BTF，服务默认关闭
  - 为节省闪存，固件**不内置** honk 核心 `/usr/bin/honk-core`（约 26 MiB）和 `geoip.dat`（`v2ray-geoip`，约 22 MiB），`geosite.dat` 仍保留
  - 使用前需自行放入 Glassyiris/honk 的 aarch64 musl 核心到 `/usr/bin/honk-core` 并 `chmod +x`，再把 `geoip.dat` 放到 `/usr/share/v2ray/`；默认路由规则会用到 `geoip:`，缺少该文件时 honk 无法按默认配置启动
- 路由器常用应用: honk 透明代理、LuCI 文件管理、uSteer、网速测试
- 软件包按 ImmortalWrt 25.12 源码构建；网速测试由 FengYinYH/luci-app-netspeedtest 的 main 分支源码构建（netspeed-engine、luci-app-netspeed），不复用 Kwrt 24.10 的二进制包

## 使用

1. 进 Actions 页手动触发 `N60Pro Firmware Build`（或等每周六自动构建）
   - 手动触发时支持在界面自定义 Root 密码、2.4G/5G Wi-Fi 名称（SSID）及 Wi-Fi 密码；留空或定时构建将使用下方默认参数。
   - 如需全新编译排查问题，可勾选「忽略缓存全新编译」。
2. 完成后到 Releases 下载固件

## 有线精简 Recovery

`N60Pro Wired Recovery Build` 是独立的手动构建任务，使用 `configs/n60pro-recovery.config`，不修改正常固件配置。源码固定为已核对的 `a99b0888b88f134f56bcb2a7d93027b5d20638a9`，上游软件源也固定版本，不加载 honk、测速等第三方源。

- 只带有线 DHCP、SSH、系统升级、NAND/UBI 恢复工具；没有 Wi-Fi、LuCI、插件或 NAT，不配置 WAN。
- 管理地址为 `10.0.0.1/24`，连接 **LAN1-LAN4**，DHCP 地址范围为 `10.0.0.100-149`。这是 recovery 的固定地址，不代表当前设备或电脑 Wi-Fi 的地址。
- 用户为 `root`；密码优先使用任务输入，留空使用 `configs/root-password.txt`，不使用空密码。通过 `ssh root@10.0.0.1` 管理。
- 使用独立源码目录和 `recovery-overlay`，不复制日常固件的 IP/Wi-Fi 设置，不加入自动刷写脚本，不复用正常固件的构建缓存。
- 构建后检查最终软件包、FIT 子镜像校验、板型、512 MiB 内存和标准 128 MiB NAND 分区布局、内核有线/闪存驱动、关键恢复工具及默认网络配置。
- 整包上限为 16 MiB，展开后的 CPIO 上限为 64 MiB，解压内核上限为 32 MiB。这些是保守的项目门槛，不是硬件上限或启动成功保证；检查使用的 TFTP 加载地址假设为 `0x46000000`，内核地址为 `0x48000000`，并不验证实际 U-Boot 环境或 ramdisk 重定位。

在 Actions 手动运行 `N60Pro Wired Recovery Build`。成功后，`n60pro-wired-recovery` 附件和 `N60Pro_WiredRecovery_*` 预发布中包含 `immortalwrt-mediatek-filogic-netcore_n60-pro-initramfs-recovery.itb`、校验文件和检查报告，不发布 sysupgrade、BL2 或 FIP。原来的正常固件任务仍会产生它自己的完整 recovery，请勿混用。

详细有线连接及启动测试说明见 [有线 Recovery 说明](docs/wired-recovery.md)，这份独立说明也随 recovery 附件发布。

**本流程尚需实际编译和实机启动验证。** 保留已经验证能恢复的官方 recovery，先确认设备使用标准分区布局以及 U-Boot 恢复模式不会自动写 NAND，再测试仅从 RAM 启动。TFTP 发送完成不是 Linux 启动成功的证据；不要仅为使用精简包而改写 BL2/FIP。

## 刷机步骤（N60 Pro）

> ⚠️ 刷机有风险，变砖可救（recovery 镜像 + TTL/有线恢复），操作前确保电量/电源稳定。

1. **刷本仓库的 U-Boot**（当前 U-Boot 不是 2025.10 时才需要）：
   - 所需 U-Boot 版本：2025.10（与本固件的 `u-boot-mt7986_netcore_n60-pro` 包一致）
   - 若设备已刷过 bl-mt798x 的 U-Boot（2022.07，分区由 NMBM 管理），本步骤会改写 `bl2` 和 `fip`，并让 UBI 从 114.5 MiB 扩大到 122.5 MiB（本仓库的分区表没有 NMBM 配置）。刷前先备份 `factory`、`u-boot-env`、`bl2`、`fip`、`ubi`，其中 `factory` 含 MAC 和校准数据。
   - 下载 Release 里的 `*-bl31-uboot.fip` 和 `*-preloader.bin`，上传到设备 `/tmp` 后改名为 `bl31-uboot.fip` 和 `preloader.bin`
   - SSH 到当前固件（原厂需先开 SSH），核对分区和文件大小：
     ```
     cat /proc/mtd
     ls -l /tmp/preloader.bin /tmp/bl31-uboot.fip
     ```
     核对要点：`/proc/mtd` 中必须有名为 `bl2` 和 `fip` 的分区，大小分别为 `00100000`（1 MiB）和 `00200000`（2 MiB），`/proc/mtd` 的 size 为十六进制。两个文件的字节数都不能超过对应分区的大小。任一条件不满足就停止，不要执行写入。本固件只面向标准 N60 Pro，已移除 512ROM 变体，分区不一致时不要刷入。
     ```
     mtd write /tmp/preloader.bin bl2
     mtd write /tmp/bl31-uboot.fip fip
     ```
   - 断电，按住 reset 上电进入 uboot（192.168.1.1）
2. **刷固件**：uboot 页面上传 `*-sysupgrade.itb` 刷写；已运行本仓库固件的设备，可在系统内用 `sysupgrade -n` 升级
3. **救砖**：下载 `*-recovery.itb`，TTL/uboot 刷入 recovery 分区

## 默认参数

- IP: `10.0.0.1`，用户 `root`，默认密码 `t29Ur9.3@casd2.`（可在 Actions 手动触发时自定义）
- 2.4GHz Wi-Fi: 默认 SSID `ChianNet-Suchuu`，密码 `kfuy4937`（WPA2-PSK，可在 Actions 手动触发时自定义）
- 5GHz Wi-Fi: 默认 SSID `ChianNet-Suchuu-5G`，密码 `kfuy4937`（WPA2-PSK，可在 Actions 手动触发时自定义）
