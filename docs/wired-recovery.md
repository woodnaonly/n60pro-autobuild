# N60 Pro 有线精简 Recovery

这是临时恢复环境，不是日常固件。只适用于标准 N60 Pro、512 MiB 内存和标准 128 MiB NAND 分区，不适用于 512ROM 或 NMBM 分区变体。

## 构建与下载

在 GitHub Actions 中手动运行 `N60Pro Wired Recovery Build`。Root 密码可在任务中输入；留空使用仓库的 `configs/root-password.txt`。

成功后下载 `n60pro-wired-recovery` 附件或 `N60Pro_WiredRecovery_*` 预发布中的：

- `*-netcore_n60-pro-initramfs-recovery.itb`
- `sha256sums` 和 `recovery-check.json`

源码和上游软件源固定版本，不使用普通固件的 overlay、插件源或构建缓存。仅发布 recovery 和诊断资料，不发布 sysupgrade、BL2 或 FIP。

## 有线连接

1. 电脑网线连接路由器 LAN1-LAN4 中任意一口，不连接 WAN。
2. 暂时关闭电脑 Wi-Fi、VPN 和网络共享，避免访问另一台设备或产生网段冲突。
3. 电脑有线接口优先自动获取地址；无法获取时可设置 `10.0.0.2/24`，不填写网关和 DNS。
4. 仅在 recovery 启动后，通过 `ssh root@10.0.0.1` 连接。没有网页管理界面和 Wi-Fi。

Recovery 的 DHCP 范围为 `10.0.0.100-149`，不向电脑提供默认网关或 DNS。`10.0.0.1` 是新 recovery 的固定管理地址，不是当前设备地址或 U-Boot/TFTP 阶段的地址；U-Boot 的服务器地址设置仍以现有恢复方式为准。

## 启动测试

**必须保留已经实机验证可恢复的官方 recovery。** 新产物尚未经过实机启动验证，静态检查通过和 TFTP 传输完成都不能证明 Linux 已正常启动。

先确认设备原有的引导程序和分区布局与标准设备一致。Recovery 中 `/proc/mtd` 来自镜像自己的设备树，单看它不能证明原有引导程序的 NAND 布局兼容。

只使用已确认不会自动写 NAND 的 U-Boot/TFTP 模式测试 RAM 启动。若当前模式会自动写入或无法确认，就停止测试。需要固定 TFTP 文件名时，只对文件改名，不修改镜像内容。

出现无有线连接、反复重启或 SSH 不可达时，返回原来已经验证有效的官方 recovery 恢复方式。不因测试本包而改写 `bl2`、`fip`、`factory` 或 `u-boot-env`。

## 检查与限制

构建流程检查最终软件包、关键恢复工具、网络设置、FIT 哈希、ARM64 内核、板型、内存和 NAND 分区布局。保守门槛为 FIT 16 MiB、展开 CPIO 64 MiB、展开内核 32 MiB；它们不是硬件上限或启动成功保证。

静态内存检查假设 TFTP 加载地址为 `0x46000000`、内核地址为 `0x48000000`，不验证设备实际 U-Boot 环境、ramdisk 重定位或运行时内存使用。检查报告中的 `hardware_boot_verified` 在当前流程中始终为 `false`。

Recovery 保留系统升级、FIT 校验及 NAND/UBI 工具，供人工诊断。没有自动刷写脚本，不提供无线、LuCI、代理、测速或 NAT；WAN 不配置。任何手动写入都需要另行核对镜像、设备和分区。
