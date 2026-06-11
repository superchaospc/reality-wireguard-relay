# reality-wireguard-relay

A [Claude Code](https://claude.com/claude-code) **skill** that teaches the agent how to
deploy a two-hop proxy chain: clients reach a **VLESS-XHTTP-REALITY** entry on a
relay/中转 VPS, and the relay forwards over a **WireGuard** tunnel to one or more
landing/落地 VPS that egress to the internet — so the public exit IP is the landing's,
not the relay's.

```
Client ──VLESS/XHTTP/REALITY──▶ Relay (中转, reachable entry)
                                  │
                                  └──WireGuard──▶ Landing (落地) ──NAT──▶ Internet
                                                  exit IP = landing's public IP(s)
```

This is not a one-click installer — it is a **playbook + helper scripts** the agent
follows to build, route, and verify the chain over SSH, one phase at a time. It captures
the design decisions and the real-world pitfalls (IP-family reachability, IPv4-forcing
the outbound, single landing behind many IPs, MTU black holes, stale MASQUERADE) that
turn into "线路不通" when missed.

## What's inside

| Path | Purpose |
|------|---------|
| `SKILL.md` | The skill entry point — when to use it and the build flow |
| `references/architecture.md` | Decision tree: single-exit vs multi-exit, fanning one entry by UUID |
| `references/pitfalls.md` | The expensive-to-debug failure modes and their fixes |
| `references/verification.md` | How to prove each phase works before moving on |
| `references/lines-spec.md` | The small JSON that drives config / verify / client-link generation |
| `scripts/gen_xray_relay_config.py` | Generate the xray relay inbound/routing config from the spec |
| `scripts/gen_client_links.py` | Generate VLESS client links / QR from the spec |
| `scripts/verify_egress.py` | Bind each tunnel source IP and confirm the public exit it lands on |
| `assets/templates/*.conf` | WireGuard `wg0.conf` templates for relay and landing |

## Install

Clone into your Claude Code skills directory:

```bash
git clone https://github.com/superchaospc/reality-wireguard-relay \
  ~/.claude/skills/reality-wireguard-relay
```

The skill activates automatically when you ask Claude Code to build a REALITY front with
a WireGuard backhaul (e.g. "搭中转走 reality 落地走 wireguard", "多出口 IP 落地",
"vless xhttp reality + wireguard 出口").

## Security note

**All IPs, UUIDs, short_ids, and keys in this repo are placeholder examples** — IPv6 uses
the `2001:db8::/32` documentation range, exit IPs use the `203.0.113.0/24` TEST-NET range,
and private keys are truncated (`UNGj…`). Generate your own secrets before deploying:

```bash
xray uuid                 # per-line UUID
xray x25519               # REALITY keypair (one pair, reused across lines)
openssl rand -hex 8       # short_id
openssl rand -hex 4       # path
```

Never commit real server IPs, UUIDs, or private keys.

## License

[MIT](LICENSE)
