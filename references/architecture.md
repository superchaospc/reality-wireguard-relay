# Architecture & decision tree

## Why this shape

- **Relay (中转)** is whatever box clients can reach. Its job is only to terminate
  VLESS-XHTTP-REALITY and shovel the decrypted traffic into a WireGuard tunnel. It is
  *not* the exit.
- **Landing (落地)** is the exit. It receives tunnel traffic and NATs it to the
  internet, so the observed exit IP is the landing's.
- **WireGuard** is in-kernel on modern Ubuntu/Debian — encryption + forwarding cost is
  negligible. Keeping the landing a *pure kernel forward + NAT* (no userspace proxy)
  is the lowest-overhead arrangement. A SOCKS/xray hop on the landing adds a userspace
  proxy round-trip for no benefit unless you specifically need per-landing routing
  logic there.

## Decision 1 — Relay entry address & client IP family

Test what's actually reachable from the outside, per family:
- From an external host *of each family*, TCP-connect the intended entry port.
- A common real case: the relay's IPv4 is GFW-blocked but its IPv6 works. Then the
  client `vless://` link must use the **IPv6** address (bracketed `[...]`), and **the
  client's network must have IPv6**. If the client has no matching family, nothing you
  do on the server fixes it — this is the usual "works on the server, 线路不通 for me".

## Decision 2 — Backhaul IP family & ForceIPv4

The WireGuard tunnel uses whatever family the **landing** has. If the landing is
IPv4-only (very common for cheap VPS), the tunnel is IPv4-only. The relay's xray
`freedom` outbound must then set `domainStrategy: "ForceIPv4"`. Otherwise, for any
destination with an AAAA record, xray opens an IPv6 connection that the v4 tunnel
can't carry — it exits the **relay's own IPv6**, leaking the relay IP and bypassing the
landing entirely.

## Decision 3 — One exit IP vs many

### Single exit IP (simplest)
- Landing: `iptables -t nat -A POSTROUTING -s <tunnel-subnet> -o <wan> -j MASQUERADE`.
- Relay: one REALITY inbound, one freedom outbound, route all proxied traffic into wg0.

### Multiple exit IPs
Goal: each "line" exits a different public IP. Two sub-cases, but the relay side is the
same idea — **one freedom outbound per line, each binding a distinct tunnel source IP
via `sendThrough`, and one routing rule per line (inboundTag→outboundTag)**.

On the landing, map each tunnel source IP to a public IP with **SNAT**:
```
-A POSTROUTING -s 10.66.66.2/32 -o eth0 -j SNAT --to-source <IP_0>
-A POSTROUTING -s 10.66.66.3/32 -o eth0 -j SNAT --to-source <IP_1>
...
```
The relay's wg0 carries several source IPs (`Address = 10.66.66.2/24, 10.66.66.3/32,
…`). A routing rule `from <tunnel-subnet> lookup <table>` sends anything sourced from a
tunnel IP into wg0; the landing's SNAT then picks the exit IP by source.

- **Many landing machines:** one tunnel per machine works too, but the single-tunnel +
  per-source-SNAT pattern above also covers "one box with many IPs" and is cheaper.
- Prefer **SNAT over MASQUERADE** for multi-exit: MASQUERADE always rewrites to the
  interface's primary IP, so it cannot give you distinct exits.

## Fanning ONE entry to several landings — split by UUID, not by port/IP

The variants above give several *exit IPs from the same landing*. A different need is
several **distinct landings** (e.g. one line → a residential SOCKS5 exit, another →
WireGuard-landing-A, another → WireGuard-landing-B) — and to let the user pick per
connection. The obvious move is one inbound per line on its own **port** or its own
**IPv6 address**. Resist it: a second inbound on `:8443`, or on an added `::b1` IPv6, may
test fine from *your* vantage yet be unreachable from the *user's* path — non-443 ports
get RST/blocked, and an extra address from the /64 is often not routed for them. You then
chase a "line B 不通" that is purely a reachability artifact (this is decision #1 biting
again, one layer down).

**Robust pattern: ONE inbound on the single proven-reachable entry, several clients
(UUIDs), and route by `user`.** Every line shares the exact same address, port, path and
shortId — only the UUID differs — so if line A reaches the entry, every line does. xray's
routing matches the inbound client's email, mapping each UUID to its own outbound:

```jsonc
// inbound: one VLESS-XHTTP-REALITY on [reachable-entry]:443, clients:
//   {id: <uuid-A>, email: "line-a"}, {id: <uuid-B>, email: "line-b"}, {id: <uuid-C>, email: "line-c"}
"routing": { "rules": [
  { "type": "field", "user": ["line-a"], "outboundTag": "socks-landing"   },  // residential socks5
  { "type": "field", "user": ["line-b"], "outboundTag": "wg-landing-A"    },  // freedom, sendThrough wgA src
  { "type": "field", "user": ["line-c"], "outboundTag": "wg-landing-B"    },  // freedom, sendThrough wgB src
  { "type": "field", "ip": ["geoip:private"], "outboundTag": "block"      }
]}
```

Each WireGuard landing is its **own** interface on the relay (`wg0`, `wg1`, …), its own
/30 + ListenPort + routing table; the outbound's `sendThrough` is that tunnel's local IP
(still with `ForceIPv4`). Outbounds may also be plain `socks` (a residential exit) or
`freedom` direct — mixing landing *types* under one entry is fine. Adding a line later =
append a client + an outbound + a `user` rule; the entry, links, and QRs for existing
lines are untouched (only the UUID is new). This is the preferred shape whenever lines
share one relay entry but need different landings.

## Decision 4 — Are the "servers" distinct machines?

Cloud providers often sell "5 IPs" that all terminate on one VM (the extra IPs are
routed/forwarded to it). Check `cat /etc/machine-id` and `curl -s4 ifconfig.co` on
each: identical values ⇒ one box. Consequences:
- You cannot run N independent WireGuard servers on N ports usefully if it's one box —
  use a single tunnel + per-source SNAT (Decision 3, multi-exit).
- Distinct exit IPs are still achievable **iff** each extra IP is usable as an egress
  *source* on that box. Confirm with a real `bind()` test (`scripts/verify_egress.py`),
  because inbound-reachable ≠ egress-usable.
- Tell the user the tradeoff: one box = single point of failure + shared bandwidth, not
  real geographic/redundancy diversity.

## Relay routing — keeping host traffic off the tunnel

If you bring up wg0 on the relay with `AllowedIPs = 0.0.0.0/0` and let wg-quick manage
routes (its default `Table = auto`), wg-quick installs a default route + fwmark rules
that send **all** host traffic through the tunnel — including your SSH session's replies
— and you lock yourself out / break the relay's own connectivity.

Instead:
- `Table = off` so wg-quick adds no routes of its own.
- A dedicated table: `ip route add default dev wg0 table 51820`.
- A selector that matches **only proxied traffic**:
  - source-based: `ip rule add from <tunnel-subnet> lookup 51820` (works great with
    `sendThrough`, since xray binds the proxied socket to a tunnel source IP), and/or
  - fwmark-based: relay outbound sets `sockopt.mark`, with `ip rule add fwmark <m>
    lookup 51820`.
- The encrypted WireGuard UDP to the landing endpoint is generated by the kernel and
  is *not* matched by these selectors, so it egresses normally via the main table — no
  routing loop.

Net effect: the relay's own default route is untouched (SSH safe); only traffic xray
emits on a tunnel source IP goes through WireGuard.
