#!/bin/bash
# Add package feeds before feeds are updated and installed.
add_feed() {
  local feed="$1"
  grep -Fqx "$feed" feeds.conf.default || printf '%s\n' "$feed" >> feeds.conf.default
}

# sirpdboy is kept only for ookla-speedtest; the speed test UI comes from FengYinYH.
# All feeds follow their default branch (main) instead of a fixed tag.
add_feed "src-git netspeedtest https://github.com/sirpdboy/netspeedtest.git;main"
add_feed "src-git netspeed https://github.com/FengYinYH/luci-app-netspeedtest.git;main"
add_feed "src-git honk https://github.com/189160/luci-app-honk.git;main"
cat feeds.conf.default
