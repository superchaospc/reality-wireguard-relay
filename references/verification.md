# Verification gates

Run these in order. Each isolates one layer, so a failure points at a specific phase.

## Gate A — WireGuard tunnel up
On the relay:
```
wg show                      # expect a recent "latest handshake" + nonzero transfer
ping -c2 <landing-tunnel-ip> # e.g. 10.66.66.1
```
0 transfer / no handshake ⇒ pitfall #6 (provider UDP firewall) or wrong keys/endpoint.

## Gate B — Per-source egress (the decisive multi-exit test)
On the relay, real-`bind()` from each tunnel source IP and check the exit IP:
```
python3 scripts/verify_egress.py --map 10.66.66.2=<exitIP0> 10.66.66.3=<exitIP1> ...
```
(or pass `--lines lines.json`). If a source returns the wrong IP, check the **landing**:
```
iptables -t nat -L POSTROUTING -nv   # SNAT pkts 0 ⇒ pitfall #2 (stale MASQUERADE)
conntrack -F                          # clear cached mappings, then retest
```
Do **not** substitute `curl --interface` here — see pitfall #3.

## Gate C — Relay host traffic unaffected (SSH safety)
On the relay:
```
curl -s4 ifconfig.co   # MUST be the relay's own public IP, not a landing IP
```
If this returns a landing IP, the tunnel hijacked the host default route → pitfall #4.

## Gate D — End-to-end per line (REALITY → tunnel → exit)
On the relay, spin up a throwaway xray client per line dialing `::1:<port>` with that
line's REALITY params, route a socks request through it, and confirm the exit IP:
```
# minimal client.json: socks inbound 127.0.0.1:10808 -> vless outbound to ::1:<port>
#   streamSettings: network xhttp, security reality,
#     realitySettings{ serverName, publicKey(pbk), shortId, fingerprint:"chrome" },
#     xhttpSettings{ path }
xray run -config /tmp/client.json &
curl -s --socks5-hostname 127.0.0.1:10808 https://api.ipify.org   # == that line's exit IP
```
`scripts/gen_xray_relay_config.py --client <lineN>` can emit this client.json for you.

## Gate E — External reachability (proves clients can connect)
From a host that has the *same IP family* as the relay entry (e.g. an IPv6-capable box
if the entry is IPv6):
```
# TCP reachability:
timeout 6 bash -c 'exec 3<>/dev/tcp/<relay-entry-ip>/<port> && echo OPEN'
# full client (same client.json as Gate D but address = the public entry IP):
xray run -config /tmp/extclient.json & ; curl --socks5-hostname 127.0.0.1:10808 https://api.ipify.org
```
If Gate D passes but the user still can't connect, the cause is almost always
client-side: the client lacks the relay entry's IP family, or an old client that can't
do xhttp. Have them check `test-ipv6.com` / `curl -6 ifconfig.co` and update the client.

## Gate F — Real-site sanity through each WireGuard line (catches the MTU black hole)
`api.ipify.org` in Gates B/D/E is a *tiny* response — it passes even when the tunnel has
an MTU black hole that breaks normal browsing (pitfall #9). So for any line whose landing
is reached over WireGuard, also fetch a **large-certificate** site end to end:
```
# through the line's client (Gate D/E client.json), or from the relay via the tunnel src:
for u in https://www.google.com/generate_204 https://github.com https://www.youtube.com; do
  curl -s --socks5-hostname 127.0.0.1:10808 -o /dev/null -w "$u -> %{http_code} %{time_total}s\n" "$u"
done
```
All should return quickly (204/200). If api.ipify.org works but these hang or time out,
it's the MTU black hole — pin `MTU = 1280` + MSS clamp on **both** wg0 ends (pitfall #9)
and probe the true inner PMTU with `ping -M do -s <size> -I <tunnel-src> <tunnel-dst>`.
The shipped wg0 templates already include this, so a fresh build should pass Gate F; this
gate matters most when adapting an existing tunnel that predates the fix.
