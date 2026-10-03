#!/bin/bash
# Add package feeds before feeds are updated and installed.
add_feed() {
  local feed="$1"
  grep -Fqx "$feed" feeds.conf.default || printf '%s\n' "$feed" >> feeds.conf.default
}

add_feed "src-git passwall_packages https://github.com/Openwrt-Passwall/openwrt-passwall-packages.git;main"
add_feed "src-git netspeedtest https://github.com/sirpdboy/netspeedtest.git;v5.2.1"
cat feeds.conf.default
