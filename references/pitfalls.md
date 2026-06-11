# Pitfalls (field-tested)

Each of these caused a real, time-consuming failure. When a verification gate fails,
match the symptom here first.

## 1. Missing `ForceIPv4` → relay leaks its own IPv6
**Symptom:** end-to-end test shows the exit IP is the *relay's* IPv6, not the landing.
**Cause:** the relay has working IPv6; xray `freedom` resolves a destination's AAAA
and connects over IPv6, which the IPv4-only WireGuard tunnel can't carry, so it goes
straight out the relay's v6.
**Fix:** set `"settings": {"domainStrategy": "ForceIPv4"}` on every freedom outbound
that should exit via the (v4) tunnel.

## 2. Stale `MASQUERADE` shadowing `SNAT` → all traffic exits the primary IP
**Symptom:** multi-exit lines all egress the landing's primary IP; the SNAT rules show
`pkts 0` in `iptables -t nat -L POSTROUTING -nv`.
**Cause:** you switched the landing from MASQUERADE to per-source SNAT by editing
wg0.conf and `systemctl restart wg-quick@wg0`. On restart, wg-quick runs the **new**
config's PostDown (which only knows the SNAT rules), so the **old** MASQUERADE rule the
previous PostUp installed is never removed. It sits above the SNAT rules and rewrites
everything to the primary IP first.
**Fix:** inspect `iptables -t nat -S POSTROUTING` and delete orphans, e.g.
`iptables -t nat -D POSTROUTING -s 10.66.66.0/24 -o eth0 -j MASQUERADE`. Then flush
conntrack (`conntrack -F`) so cached mappings don't mask the fix.
**Prevention:** when changing NAT mode, stop wg first (`wg-quick down wg0`) *before*
rewriting the conf, or flush the relevant rules explicitly.

## 3. `curl --interface <ip>` does not reliably bind the source
**Symptom:** testing per-source egress with `curl --interface 10.66.66.3 ifconfig.co`
returns the wrong/primary exit IP, even though routing is correct.
**Cause:** curl's `--interface` with an IP did not actually bind that source here;
packets left with the primary tunnel IP.
**Fix:** test with a real `bind()` — that's exactly what xray's `sendThrough` does. Use
`scripts/verify_egress.py` (python socket binds the source, then connects). `ip route
get <dst> from <src>` and a python `bind()`→`connect()` are the trustworthy checks.

## 4. AllowedIPs 0.0.0.0/0 + default wg-quick routing hijacks the relay's route
**Symptom:** you bring up wg0 on the relay and your SSH session freezes / the relay
loses normal connectivity.
**Cause:** with `AllowedIPs = 0.0.0.0/0` and wg-quick's default `Table = auto`,
wg-quick installs a default route through wg0 for *all* traffic.
**Fix:** `Table = off` on the relay interface; add your own `table 51820` with a
default via wg0 and a selector (`ip rule from <tunnel-subnet>` and/or `fwmark`) so only
proxied traffic uses it.

## 5. "N landing servers" that are actually one box
**Symptom:** several SSH targets, same `machine-id`, same `curl -s4 ifconfig.co`.
**Cause:** provider routed several public IPs to a single VM.
**Fix:** treat as one box with multiple IPs → single tunnel + per-source SNAT. Confirm
each IP is egress-usable (real `bind()` test). Tell the user it's a single point of
failure with shared bandwidth, not redundancy.

## 6. Provider firewall blocks the WireGuard UDP port
**Symptom:** `wg show` never shows a handshake; `transfer` stays at 0.
**Cause:** the cloud security group blocks inbound UDP on the WG ListenPort.
**Fix:** open the port (default 51820/udp) in the provider panel. Re-test handshake.

## 7. REALITY + XHTTP transport details
- For `network: xhttp` keep `flow` **empty**. `xtls-rprx-vision` is for raw TCP+REALITY
  only; pairing it with xhttp breaks the handshake.
- Listen on `::` so the inbound is dual-stack; confirm with a `::1` loopback client.
- Reuse one REALITY keypair across lines is fine; lines differ by port + UUID
  (+ shortId/path). The client `pbk` is the REALITY *public* key.
- Recent Xray uses `target` + `serverNames` in `realitySettings`; `dest` is the older
  alias. `xray run -test` will tell you if the schema is off.

## 8. Reused/reinstalled IPs break SSH host-key checks
`ssh-keygen -R <ip>` before connecting to a box whose IP was recycled, or you'll hit
REMOTE HOST IDENTIFICATION HAS CHANGED and be unable to log in.

## 9. WireGuard MTU black hole → "most sites hang on the TLS handshake"
**Symptom:** the chain "works" but is maddeningly selective — a few sites load
(Cloudflare, Wikipedia — small TLS responses) while most hang then time out (Google,
YouTube, GitHub, Microsoft — large certificate chains). `ping` succeeds everywhere, and
a tiny request like `curl https://api.ipify.org` returns fine. The smallness is the
trap: it makes a broken tunnel look healthy, so you chase the wrong layer (keys, REALITY,
client config) for an hour.

**Cause:** the WireGuard interface MTU (wg-quick's default ~1420) is larger than the
path can actually carry between relay and landing — frequently ~1280. The big TLS
ServerHello+certificate packets exceed the real PMTU and are **silently dropped** (the
middle filters the ICMP "fragmentation needed", so PMTU discovery never kicks in and the
flow just stalls after the handshake starts). Small responses fit, so they survive.

**The measurement trap:** `ping -M do -s <size>` over the *underlay* (both boxes' eth0,
relay→landing public IP) can report a clean 1500 while the actual WG-carrying **UDP** is
capped lower by the carrier — ICMP and large UDP are treated differently. So "both eth0
are 1500 and the underlay pings 1500" does **not** mean the WG inner path passes 1420.
A directly-egressing landing (no second tunnel) can still exhibit this; the cap is on the
HK↔landing carrier path, not on encapsulation you can see.

**Diagnose:** probe the *inner* path from a tunnel source IP and grow the size until it
drops:
```
for s in 1200 1300 1380 1400; do ping -M do -s $s -c1 -W2 -I <relay-tunnel-ip> <landing-tunnel-ip> \
  && echo "$s ok" || echo "$s DROP"; done     # 1200 ok / 1300 DROP ⇒ real MTU ≈ 1280
```
Then confirm with a **big-cert HTTPS site through the chain**, never api.ipify.org.

**Fix (symmetric — BOTH ends):** pin `MTU = 1280` on each wg0 (IPv6 floor, universally
safe) and clamp TCP MSS. The templates in `assets/templates/` already bake this in:
relay clamps on `OUTPUT -o wg0` (it originates the proxied sockets), landing clamps on
`FORWARD -o wg0` (it forwards replies into the tunnel). MSS covers TCP both directions;
the MTU floor additionally covers UDP/QUIC (YouTube/Google default to QUIC, so don't
skip it). Apply live without bouncing the tunnel: `ip link set dev wg0 mtu 1280` plus the
iptables clamp, then persist in wg0.conf so it survives reboot.

**Why 1280 and not auto:** wg-quick derives MTU from the route to the *endpoint* (eth0
1500 → 1420), which only accounts for the first hop and is blind to a lower cap further
along. 1280 is the IPv6 minimum every path must carry, so it can't be black-holed.
