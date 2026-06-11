#!/usr/bin/env python3
"""Generate the relay's xray config (one VLESS-XHTTP-REALITY inbound per exit line, each
freedom outbound ForceIPv4 + sendThrough its tunnel source IP, routing inbound->outbound).

    python3 gen_xray_relay_config.py --lines lines.json > config.json
    python3 gen_xray_relay_config.py --lines lines.json --client exit-244 > client.json

--client emits a throwaway client config (socks 127.0.0.1:10808 -> that line via ::1)
for the end-to-end verification gate (Gate D). Point its outbound address at the public
entry_host instead of ::1 for the external gate (Gate E) by editing one field.

See references/lines-spec.md for the lines.json schema.
"""
import argparse, json, sys


def server_config(spec: dict) -> dict:
    priv = spec["reality_private_key"]
    sni = spec["sni"]
    inbounds, outbounds, rules = [], [], []
    for i, ln in enumerate(spec["lines"], 1):
        tag_in, tag_out = f"in-{i}", f"out-{i}"
        inbounds.append({
            "tag": tag_in,
            "listen": "::",
            "port": ln["port"],
            "protocol": "vless",
            "settings": {"clients": [{"id": ln["uuid"]}], "decryption": "none"},
            "streamSettings": {
                "network": "xhttp",
                "security": "reality",
                "realitySettings": {
                    "target": f"{sni}:443",
                    "serverNames": [sni],
                    "privateKey": priv,
                    "shortIds": [ln["short_id"]],
                },
                "xhttpSettings": {"path": "/" + ln["path"].lstrip("/")},
            },
        })
        outbounds.append({
            "tag": tag_out,
            "protocol": "freedom",
            "sendThrough": ln["send_through"],
            "settings": {"domainStrategy": "ForceIPv4"},
        })
        rules.append({"type": "field", "inboundTag": [tag_in], "outboundTag": tag_out})
    return {"log": {"loglevel": "warning"},
            "inbounds": inbounds, "outbounds": outbounds,
            "routing": {"rules": rules}}


def client_config(spec: dict, name: str, address: str | None) -> dict:
    ln = next((l for l in spec["lines"] if l["name"] == name), None)
    if ln is None:
        sys.exit(f"no line named {name!r}; have: "
                 + ", ".join(l['name'] for l in spec['lines']))
    addr = address or "::1"
    return {
        "inbounds": [{"listen": "127.0.0.1", "port": 10808,
                      "protocol": "socks", "settings": {"udp": False}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{"address": addr, "port": ln["port"],
                                    "users": [{"id": ln["uuid"], "encryption": "none"}]}]},
            "streamSettings": {
                "network": "xhttp",
                "security": "reality",
                "realitySettings": {"serverName": spec["sni"],
                                    "publicKey": spec["reality_public_key"],
                                    "shortId": ln["short_id"], "fingerprint": "chrome"},
                "xhttpSettings": {"path": "/" + ln["path"].lstrip("/")},
            },
        }],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lines", required=True)
    ap.add_argument("--client", metavar="LINE_NAME",
                    help="emit a test client config for this line instead of the server")
    ap.add_argument("--address",
                    help="override client outbound address (e.g. public entry_host for Gate E)")
    args = ap.parse_args()
    spec = json.load(open(args.lines))
    cfg = (client_config(spec, args.client, args.address)
           if args.client else server_config(spec))
    print(json.dumps(cfg, indent=2))


if __name__ == "__main__":
    main()
