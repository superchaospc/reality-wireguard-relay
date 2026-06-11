#!/usr/bin/env python3
"""Verify per-source egress on the RELAY by binding each WireGuard tunnel source IP and
checking the public exit IP it lands on.

This uses a real socket bind() — the same thing xray's `sendThrough` does — because
`curl --interface <ip>` does NOT reliably bind the source here (see pitfalls #3).

Run ON the relay, after the tunnel + landing NAT are up:

    python3 verify_egress.py --map 10.66.66.2=203.0.113.10 10.66.66.3=203.0.113.11
    python3 verify_egress.py --lines lines.json     # reads send_through + exit_ip

Exit code is non-zero if any source maps to the wrong exit IP.
"""
import argparse, json, socket, sys


def egress_ip(src_ip: str, timeout: float = 8.0) -> str:
    """Bind to src_ip, HTTP GET api.ipify.org over port 80, return the reported IP."""
    host = "api.ipify.org"
    dst = socket.gethostbyname(host)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((src_ip, 0))
        s.settimeout(timeout)
        s.connect((dst, 80))
        s.sendall(
            f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode()
        )
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        return data.split(b"\r\n\r\n", 1)[-1].decode(errors="replace").strip()
    finally:
        s.close()


def load_map(args) -> dict:
    if args.lines:
        spec = json.load(open(args.lines))
        return {l["send_through"]: l.get("exit_ip", "") for l in spec["lines"]}
    out = {}
    for item in args.map or []:
        src, _, exp = item.partition("=")
        out[src] = exp
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", nargs="*", help="src=expected_exit pairs")
    ap.add_argument("--lines", help="lines.json spec (uses send_through=exit_ip)")
    args = ap.parse_args()

    mapping = load_map(args)
    if not mapping:
        ap.error("provide --map or --lines")

    ok = True
    for src, expected in mapping.items():
        try:
            got = egress_ip(src)
        except Exception as e:
            got, good = f"ERROR {e}", False
        else:
            good = (not expected) or (got == expected)
        ok = ok and good
        tag = "OK " if good else "BAD"
        suffix = f"  (expect {expected})" if expected else ""
        print(f"{tag} src {src} -> {got}{suffix}")
    print("ALL_GOOD" if ok else "MISMATCH — see pitfalls #2 (stale MASQUERADE) / #3")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
