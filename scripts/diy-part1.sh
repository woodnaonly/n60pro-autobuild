#!/bin/bash
# Add package feeds before feeds are updated and installed.
add_feed() {
  local feed="$1"
  grep -Fqx "$feed" feeds.conf.default || printf '%s\n' "$feed" >> feeds.conf.default
}

# sirpdboy is kept only for ookla-speedtest; the speed test UI comes from FengYinYH.
add_feed "src-git netspeedtest https://github.com/sirpdboy/netspeedtest.git;v5.2.1"
add_feed "src-git netspeed https://github.com/FengYinYH/luci-app-netspeedtest.git;v1.0.0-r2"
add_feed "src-git honk https://github.com/189160/luci-app-honk.git;honk_2026.10.09"
cat feeds.conf.default
