---
name: reality-wireguard-relay
description: >-
  Deploy a two-hop proxy chain where clients reach a VLESS-XHTTP-REALITY entry on
  a relay/中转 VPS, and the relay forwards over a WireGuard tunnel to one or more
  landing/落地 VPS that egress to the internet (so the exit IP is the landing's, not
  the relay's). Use this whenever the user wants to 搭中转+落地 / 中转走 reality 落地走
  wireguard / build a REALITY front with a WireGuard backhaul, expose multiple exit
  IPs from landing machines, hide a GFW-blocked relay IPv4 behind its IPv6, or chain
  an xray REALITY inbound to a WireGuard NAT/SNAT exit. Triggers on "中转 reality 落地
  wireguard", "vless xhttp reality + wireguard 出口", "relay to landing via wireguard",
  "多出口 IP 落地", even when not phrased exactly. NOT for the user's one-click
  superchaospc/xray-relay SOCKS5/直连 script (that's the xray-relay-deploy skill) and
  NOT for plain single-box VLESS setups with no WireGuard backhaul.
---

# REALITY → WireGuard relay/landing chain

Build the topology:

```
Client ──VLESS/XHTTP/REALITY──▶ Relay (中转, reachable entry)
                                  │
                                  └──WireGuard──▶ Landing (落地) ──NAT──▶ Internet
                                                  exit IP = landing's public IP(s)
```

The **relay** terminates REALITY and forwards proxied traffic into a WireGuard tunnel.
The **landing** does the real egress. Keep the landing as a **pure kernel WireGuard
forward + NAT** with **no userspace proxy** — that is the lowest-overhead design and
should be the default. Only run xray/socks on the landing if the user has a concrete
reason.

This skill assumes SSH root access to both ends. It drives the boxes over SSH and is
non-interactive. Work one phase at a time and **verify each phase before moving on** —
silent misconfig here looks like "线路不通" later and is expensive to chase.

## Before anything: settle the design (read references/architecture.md)

Four decisions shape everything. Resolve them up front; don't guess:

1. **Which relay address can clients actually reach?** A relay's IPv4 is often
   GFW-blocked while its IPv6 still works (or vice-versa). The client link must point
   at the *reachable* family, and **the client must have that same IP family**. Confirm
   this — it is the #1 real-world cause of "connects on the server but not for me".
2. **What IP family does the WireGuard backhaul use?** Whatever the *landing* has. If
   the landing has no IPv6, the tunnel is IPv4-only → the relay's outbound **must force
   IPv4** (see pitfalls), or v6-bound proxy traffic leaks straight out the relay.
3. **One exit IP or many — and one landing or several?** Several exit IPs from *one*
   landing → per-source `SNAT` + one relay line per exit IP. Several *distinct landings*
   under one entry (e.g. socks5 exit + WG-landing-A + WG-landing-B, user-selectable) →
   **one inbound, several UUIDs, route by `user`** — not a port/IP per line, which tends
   to be unreachable on the client's path. See architecture.md "Fanning one entry".
4. **Are the "N landing servers" actually N machines?** Cloud accounts frequently hand
   out several IPs that all land on **one box**. Building N WireGuard tunnels to one box
   is pointless and conflicts on ports. **Verify machine identity first** (Phase 1) —
   this check has saved entire rebuilds.

`references/architecture.md` has the full decision tree, the single-exit vs multi-exit
variants, and why each piece is shaped the way it is. Read it before building.

## Build phases

Track these as todos and do them in order.

### Phase 0 — SSH access
Push your key to every box so the rest is non-interactive. If only a password is
known, use `sshpass -p '<pw>' ssh-copy-id -o StrictHostKeyChecking=accept-new -i
<pubkey> <host>`. Clear any stale host key first (`ssh-keygen -R <ip>`) — a reused/
reinstalled IP triggers REMOTE HOST IDENTIFICATION CHANGED and blocks login.

### Phase 1 — Verify topology (do NOT skip)
On each claimed landing, collect identity + reachability:
```
cat /etc/machine-id ; curl -s4 ifconfig.co ; curl -s6 ifconfig.co ; ip -br addr show
```
- Same `machine-id` + same egress IP across "several servers" ⇒ **one box, multiple
  IPs**. Switch to the multi-exit-on-one-box variant (single tunnel + per-source SNAT).
- Note each box's IP families. Confirm decision #2 from here.
- If extra IPs are bound to one box, confirm each is usable as an egress *source*
  (test with a real `bind()`, see Phase 5 / `scripts/verify_egress.py`) before
  promising distinct exit IPs.

### Phase 2 — WireGuard tunnel
Install on both ends (`apt-get install -y wireguard wireguard-tools iptables`),
generate a keypair on each, exchange public keys. Use the config templates in
`assets/templates/` (`landing-wg0.conf`, `relay-wg0.conf`). Pick a tunnel subnet
(default `10.66.66.0/24`, landing `.1`, relay `.2`, extra relay source IPs `.3+`).
The templates pin **`MTU = 1280` + an MSS clamp on both ends** — keep it. The path
carrying the WG UDP often can't pass a 1420-byte inner packet even when both eth0s look
like 1500, which silently black-holes large TLS handshakes later (pitfall #9). 1280 is
the safe floor; don't "optimize" it back up without proving the inner PMTU.
`systemctl enable --now wg-quick@wg0`. **Verify:** `wg show` shows a recent handshake
and the relay can `ping <landing tunnel IP>`.

### Phase 3 — Landing NAT/egress
- Enable forwarding persistently: `net.ipv4.ip_forward=1` in `/etc/sysctl.d/`.
- **Single exit IP:** `MASQUERADE` for the tunnel subnet out the WAN iface.
- **Multiple exit IPs:** one `SNAT --to-source <public IP>` rule **per tunnel source
  IP** (`-s 10.66.66.3 → IP_a`, `-s 10.66.66.4 → IP_b`, …). Put the rules in the
  wg0.conf PostUp/PostDown so they track the interface.
- Landing runs **no xray** in the default design.

### Phase 4 — Relay routing (keep the host's own traffic off the tunnel)
The relay must send *only proxied traffic* through WireGuard, never its own SSH/system
traffic. Use `Table = off` on the relay's wg0 and a dedicated routing table:
`ip route add default dev wg0 table 51820` plus a rule selecting proxied traffic
(`ip rule add from <tunnel-subnet> table 51820`, and/or an `fwmark` rule). See the
relay template and `references/architecture.md`. **Verify:** the relay's *own* default
egress is still its own public IP (so SSH stays up), while traffic bound to a tunnel
source IP exits via the landing.

### Phase 5 — Relay xray (VLESS-XHTTP-REALITY)
Install xray (`bash -c "$(curl -sL https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install`).
Generate `xray uuid`, `xray x25519` (REALITY keypair), `openssl rand -hex 8` (shortId),
`openssl rand -hex 4` (path) — one set per line. Build the config with
`scripts/gen_xray_relay_config.py` (one inbound per exit, each freedom outbound with
`domainStrategy: ForceIPv4` + `sendThrough` its tunnel source IP, routing inboundTag→
outboundTag). `xray run -test -config ...` then restart. **Verify:** all ports listen
on `::` (dual-stack).

### Phase 6 — Verify end to end (the gates that catch the real bugs)
Run in this order; each isolates a layer:
1. **Per-source egress** (`scripts/verify_egress.py` on the relay): real-`bind()` from
   each tunnel source IP → expect the matching landing exit IP. If wrong, also check
   `iptables -t nat -L POSTROUTING -nv` counters on the landing.
2. **End-to-end per line:** a throwaway xray client on the relay dialing `::1:<port>`
   with each line's REALITY params → exit IP must match.
3. **External reachability:** from a host with the right IP family, TCP-connect the
   relay entry, then run a real client → exit IP. Proves clients can actually reach it.
4. **Real-site sanity (WireGuard lines):** the IP checks above use a *tiny* response that
   passes even through an MTU-black-holed tunnel. Also fetch a **big-cert** site
   (google/github/youtube) end to end — if those hang while api.ipify.org works, it's
   pitfall #9. Never sign off a WG line on api.ipify.org alone.

`references/verification.md` has copy-paste test snippets (Gates A–F).

### Phase 7 — Client links + QR
`scripts/gen_client_links.py` emits the `vless://…` links and QR PNGs. The QR avoids
copy-paste corruption (IPv6 brackets, `#`, `&` get mangled in chat apps), which matters
when handing a config to a different device. Remind the user the client needs the same
IP family as the relay entry.

## Pitfalls — read references/pitfalls.md

These are real failures seen in the field; each wasted significant time. Skim the file
before building, and revisit it the moment a verification gate fails:

- **Missing `ForceIPv4`** on the relay outbound → v6-bound proxy traffic leaks the
  relay's own IPv6 instead of going through the v4 tunnel.
- **Stale `MASQUERADE` shadowing `SNAT`** after a MASQUERADE→SNAT switch (wg-quick
  restart runs the *new* PostDown, never removing the *old* PostUp rule) → everything
  exits the primary IP, SNAT counters stuck at 0.
- **`curl --interface <ip>` does not reliably bind the source** here — it silently
  used the primary IP in testing. Verify per-source egress with a real `bind()`
  (python socket, which is what xray `sendThrough` does), never with `curl --interface`.
- **AllowedIPs `0.0.0.0/0` with wg-quick's default routing on the relay hijacks the
  host default route** and kills your SSH. Always `Table = off` + your own table.
- **"N servers" that are 1 box** (Phase 1).
- **Provider firewall blocking the WireGuard UDP port** → handshake never completes,
  `wg show` shows 0 transfer. Open it in the cloud panel.
- **MTU black hole** → most sites hang on the TLS handshake while a few load and tiny
  requests pass. Pin `MTU = 1280` + MSS clamp on both wg0 ends (baked into the templates;
  pitfall #9). Verify with Gate F, not api.ipify.org.

## Helper scripts

- `scripts/verify_egress.py` — run on the relay; real-`bind()` per-source egress test.
- `scripts/gen_xray_relay_config.py` — generate the multi-line REALITY xray config.
- `scripts/gen_client_links.py` — emit `vless://` links + QR PNGs (needs `segno`).

Run each with `--help`. They take a small JSON "lines" spec (see `references/lines-spec.md`).
