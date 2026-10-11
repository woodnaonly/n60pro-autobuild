# N60 Pro 自动编译固件

磊科 N60 Pro (MT7986A) 专用在线编译模板，产物自动发布到 [Releases](../../releases)。

## 固件特性

- 源码: [chasey-dev/immortalwrt-mt798x-rebase](https://github.com/chasey-dev/immortalwrt-mt798x-rebase) `25.12` 分支（MTK 原厂有线/无线驱动 + HNAT）
- USB 存储支持（USB 3.0、UAS、automount；与当前路由器包配置一致）
- 不包含 USB 蜂窝模组驱动或拨号工具
- MTK HNAT 硬件加速（`luci-app-turboacc-mtk`）
- honk 透明代理：LuCI 界面与打包来自 189160/luci-app-honk，核心取 Glassyiris/honk（daeuniverse/honk 的 fork）预编译包，内核开启 BTF，服务默认关闭
- 路由器常用应用: honk 透明代理、LuCI 文件管理、uSteer、网速测试
- 软件包按 ImmortalWrt 25.12 源码构建；网速测试由 FengYinYH/luci-app-netspeedtest v1.0.0-r2 源码构建（netspeed-engine、luci-app-netspeed），不复用 Kwrt 24.10 的二进制包

## 使用

1. 进 Actions 页手动触发 `N60Pro Firmware Build`（或等每周六自动构建）
   - 手动触发时支持在界面自定义 Root 密码、2.4G/5G Wi-Fi 名称（SSID）及 Wi-Fi 密码；留空或定时构建将使用下方默认参数。
   - 如需全新编译排查问题，可勾选「忽略缓存全新编译」。
2. 完成后到 Releases 下载固件

## 刷机步骤（N60 Pro）

> ⚠️ 刷机有风险，变砖可救（recovery 镜像 + TTL/有线恢复），操作前确保电量/电源稳定。

1. **刷第三方 uboot**（如果还没刷）：
   - 所需 U-Boot 版本：2025.10（与本固件的 `u-boot-mt7986_netcore_n60-pro` 包一致）
   - 下载 Release 里的 `bl31-uboot.fip` 和 `preloader.bin`
   - SSH 到当前固件（原厂需先开 SSH），上传后先核对分区：
     ```
     cat /proc/mtd
     ls -l /tmp/preloader.bin /tmp/bl31-uboot.fip
     ```
     核对要点：`/proc/mtd` 中必须有名为 `Preloader` 和 `FIP` 的分区，两个文件的字节数都不能超过对应分区的大小（`/proc/mtd` 的 size 为十六进制，需换算）。任一条件不满足就停止，不要执行写入。本固件只面向标准 N60 Pro，已移除 512ROM 变体，分区不一致时不要刷入。
     ```
     mtd write /tmp/preloader.bin Preloader
     mtd write /tmp/bl31-uboot.fip FIP
     ```
   - 断电，按住 reset 上电进入 uboot（192.168.1.1）
2. **刷固件**：uboot 页面上传 `*-sysupgrade.itb` 刷写；已在本模板固件上的用 `sysupgrade -n` 升级
3. **救砖**：下载 `*-recovery.itb`，TTL/uboot 刷入 recovery 分区

## 默认参数

- IP: `10.0.0.1`，用户 `root`，默认密码 `t29Ur9.3@casd2.`（可在 Actions 手动触发时自定义）
- 2.4GHz Wi-Fi: 默认 SSID `ChianNet-Suchuu`，密码 `kfuy4937`（WPA2-PSK，可在 Actions 手动触发时自定义）
- 5GHz Wi-Fi: 默认 SSID `ChianNet-Suchuu-5G`，密码 `kfuy4937`（WPA2-PSK，可在 Actions 手动触发时自定义）
