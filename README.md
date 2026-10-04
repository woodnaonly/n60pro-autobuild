# N60 Pro 自动编译固件

磊科 N60 Pro (MT7986A) 专用在线编译模板，产物自动发布到 [Releases](../../releases)。

## 固件特性

- 源码: [chasey-dev/immortalwrt-mt798x-rebase](https://github.com/chasey-dev/immortalwrt-mt798x-rebase) `25.12` 分支（MTK 原厂有线/无线驱动 + HNAT）
- USB 存储支持（USB 3.0、UAS、automount；与当前路由器包配置一致）
- 不包含 USB 蜂窝模组驱动或拨号工具
- MTK HNAT 硬件加速（`luci-app-turboacc-mtk`）
- 路由器常用应用: PassWall、多协议代理核心、LuCI 文件管理、uSteer、网速测试
- 软件包按 ImmortalWrt 25.12 源码构建；网速测试使用当前上游依赖，不复用 Kwrt 24.10 的二进制包
- 旧版 Kwrt 的 `shadowsocks-libev` 分包不在目标源码中，使用目标源码可构建的代理核心
- 512MB 闪存大分区布局（ubi=490MB 吃满，适配恩山 WildEdition U-Boot `506.5MB` 分区表）

## 使用

1. 进 Actions 页手动触发 `N60Pro Firmware Build`（或等每周六自动构建）
   - 手动触发时支持在界面自定义 Root 密码、2.4G/5G Wi-Fi 名称（SSID）及 Wi-Fi 密码；留空或定时构建将使用下方默认参数。
   - 如需全新编译排查问题，可勾选「忽略缓存全新编译」。
2. 完成后到 Releases 下载固件

## 刷机步骤（N60 Pro）

> ⚠️ 刷机有风险，变砖可救（recovery 镜像 + TTL/有线恢复），操作前确保电量/电源稳定。

1. **刷第三方 uboot**（如果还没刷）：
   - 下载 Release 里的 `bl31-uboot.fip` 和 `preloader.bin`
   - SSH 到当前固件（原厂需先开 SSH），上传后：
     ```
     mtd write /tmp/preloader.bin Preloader
     mtd write /tmp/bl31-uboot.fip FIP
     ```
   - 断电，按住 reset 上电进入 uboot（192.168.1.1）
2. **刷固件**：uboot 页面上传 `*-sysupgrade.itb` 刷写；已在本模板固件上的用 `sysupgrade -n` 升级
3. **救砖**：下载 `*-recovery.itb`，TTL/uboot 刷入 recovery 分区

## 默认参数

- IP: `192.168.1.1`，用户 `root`，默认密码 `t29Ur9.3@casd2.`（可在 Actions 手动触发时自定义）
- 2.4GHz Wi-Fi: 默认 SSID `ChianNet-Suchuu`，密码 `kfuy4937`（WPA2-PSK，可在 Actions 手动触发时自定义）
- 5GHz Wi-Fi: 默认 SSID `ChianNet-Suchuu-5G`，密码 `kfuy4937`（WPA2-PSK，可在 Actions 手动触发时自定义）
