#!/usr/bin/env python3
import os
import re
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: configure-wifi.py <path-to-99-default-wifi>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isfile(path):
        print(f"::error::Wi-Fi defaults file not found: {path}", file=sys.stderr)
        sys.exit(1)

    ssid_2g = os.environ.get("INPUT_WIFI_SSID_2G")
    ssid_5g = os.environ.get("INPUT_WIFI_SSID_5G")
    wifi_pass = os.environ.get("INPUT_WIFI_PASSWORD")

    if not ssid_2g:
        ssid_2g = "ChianNet-Suchuu"
    if not ssid_5g:
        ssid_5g = "ChianNet-Suchuu-5G"
    if not wifi_pass:
        wifi_pass = "kfuy4937"

    if not ssid_2g.strip():
        print("::error::2.4GHz Wi-Fi SSID cannot be empty", file=sys.stderr)
        sys.exit(1)
    if not ssid_5g.strip():
        print("::error::5GHz Wi-Fi SSID cannot be empty", file=sys.stderr)
        sys.exit(1)
    if len(wifi_pass) < 8 or len(wifi_pass) > 63:
        print("::error::Wi-Fi password must be between 8 and 63 characters", file=sys.stderr)
        sys.exit(1)

    def sh_quote(s):
        return "'" + s.replace("'", "'\"'\"'") + "'"

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern_2g = r"configure_band 2g .*"
    pattern_5g = r"configure_band 5g .*"

    new_2g = f"configure_band 2g {sh_quote(ssid_2g)} {sh_quote(wifi_pass)}"
    new_5g = f"configure_band 5g {sh_quote(ssid_5g)} {sh_quote(wifi_pass)}"

    content, count_2g = re.subn(pattern_2g, new_2g, content)
    content, count_5g = re.subn(pattern_5g, new_5g, content)

    if count_2g != 1 or count_5g != 1:
        print(f"::error::Expected 1 replacement for each band in {path}, got 2g={count_2g}, 5g={count_5g}", file=sys.stderr)
        sys.exit(1)

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    print(f"Wi-Fi defaults configured successfully: 2.4G={ssid_2g}, 5G={ssid_5g}")

if __name__ == "__main__":
    main()
