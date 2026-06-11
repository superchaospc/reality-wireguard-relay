#!/usr/bin/env python3
"""Emit vless:// client links + QR PNGs for each line in a lines.json spec.

    pip install --user segno          # one-time (pure-python QR, no Pillow needed)
    python3 gen_client_links.py --lines lines.json --out ./client-links

Writes <out>/all-links.txt and <out>/<line-name>.png. QR avoids copy-paste corruption
of IPv6 brackets / # / & in chat apps — hand the PNG to the other device. Reminder: the
client must have the same IP family as entry_host.

See references/lines-spec.md for the schema.
"""
import argparse, json, os, sys


def build_link(spec: dict, ln: dict) -> str:
    host = spec["entry_host"]
    fam = spec.get("entry_family", "")
    is_v6 = (fam == "ipv6") or (":" in host and not host.startswith("["))
    addr = f"[{host}]" if is_v6 else host
    q = (f"encryption=none&security=reality&sni={spec['sni']}&fp=chrome"
         f"&pbk={spec['reality_public_key']}&sid={ln['short_id']}"
         f"&type=xhttp&path=%2F{ln['path'].lstrip('/')}&mode=auto")
    return f"vless://{ln['uuid']}@{addr}:{ln['port']}?{q}#{ln['name']}"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lines", required=True)
    ap.add_argument("--out", default="./client-links")
    ap.add_argument("--no-qr", action="store_true", help="links only, skip PNGs")
    args = ap.parse_args()

    spec = json.load(open(args.lines))
    os.makedirs(args.out, exist_ok=True)

    segno = None
    if not args.no_qr:
        try:
            import segno  # noqa
        except ImportError:
            print("segno not installed (pip install --user segno); writing links only.",
                  file=sys.stderr)

    txt = []
    for ln in spec["lines"]:
        link = build_link(spec, ln)
        label = ln["name"] + (f"  exit {ln['exit_ip']}" if ln.get("exit_ip") else "")
        txt.append(f"# {label}  port {ln['port']}\n{link}")
        if segno:
            segno.make(link, error="m").save(
                os.path.join(args.out, f"{ln['name']}.png"), scale=8, border=3)
    open(os.path.join(args.out, "all-links.txt"), "w").write("\n\n".join(txt) + "\n")
    print(f"wrote {len(spec['lines'])} link(s) to {args.out}")
    for f in sorted(os.listdir(args.out)):
        print("  ", f)


if __name__ == "__main__":
    main()
