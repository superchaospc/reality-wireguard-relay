# The "lines" spec

All three scripts read a small JSON describing the relay's REALITY entry and one
"line" (= one exit IP) per entry. One file drives config generation, verification, and
client-link/QR generation, so values stay consistent.

```json
{
  "entry_host": "2001:db8:1907::1",
  "entry_family": "ipv6",
  "reality_private_key": "UNGj…",
  "reality_public_key":  "QPsn…",
  "sni": "www.microsoft.com",
  "lines": [
    {
      "name": "exit-a",
      "port": 443,
      "uuid": "11111111-2222-3333-4444-555555555555",
      "short_id": "0123456789abcdef",
      "path": "a1b2c3d4",
      "send_through": "10.66.66.2",
      "exit_ip": "203.0.113.10"
    }
  ]
}
```

Field notes:
- `entry_host` — the address clients dial (the *reachable* family; bracketed
  automatically for IPv6 in links).
- `reality_private_key` lives only on the relay (xray inbound); `reality_public_key`
  (`pbk`) goes to clients. Generate with `xray x25519`.
- `send_through` — the relay-side WireGuard source IP for this line; the landing SNATs
  that source to `exit_ip`.
- `exit_ip` — used by the scripts only for verification/labels, not written into xray.
- For a **single-exit** deployment there is just one line and the landing uses
  MASQUERADE; `send_through` can be the single tunnel IP and `exit_ip` the landing IP.

Generate per-line secrets on the relay:
```
xray uuid                 # uuid
xray x25519               # reality keypair (one pair, reused across lines)
openssl rand -hex 8       # short_id
openssl rand -hex 4       # path
```
