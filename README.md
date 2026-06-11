# reality-wireguard-relay

[![Release](https://img.shields.io/github/v/release/superchaospc/reality-wireguard-relay?color=success)](https://github.com/superchaospc/reality-wireguard-relay/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-8A2BE2)](https://claude.com/claude-code)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-412991)](#install)
[![Xray REALITY + WireGuard](https://img.shields.io/badge/Xray-REALITY%20%2B%20WireGuard-orange)](#)

**English** | [中文说明](#中文说明)

A [Claude Code](https://claude.com/claude-code) / **Codex** **skill** that teaches the agent how to
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

That's all you need for **Claude Code**. To use it in **Codex** too, run the bundled
installer once — Claude Code and Codex share the same `SKILL.md` format, so one copy
serves both; the script just symlinks the skill into Codex's skill dirs
(`~/.codex/skills`, `~/.agents/skills`):

```bash
~/.claude/skills/reality-wireguard-relay/install.sh
```

It's self-contained (no other skill required), portable (agents that aren't installed are
skipped), and idempotent. Restart Codex (new session) so it rescans.

The skill activates automatically when you ask the agent to build a REALITY front with
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

---

## 中文说明

一个 [Claude Code](https://claude.com/claude-code) / **Codex** **skill**，教 agent 搭建两跳代理链：客户端连接
**中转 VPS** 上的 **VLESS-XHTTP-REALITY** 入口，中转再通过 **WireGuard** 隧道把流量转发给一台或多台
**落地 VPS** 出网——所以公网出口 IP 是落地的，而不是中转的。

```
客户端 ──VLESS/XHTTP/REALITY──▶ 中转 (relay, 可达入口)
                                  │
                                  └──WireGuard──▶ 落地 (landing) ──NAT──▶ 互联网
                                                  出口 IP = 落地的公网 IP
```

这不是一键安装脚本，而是一份 **操作手册 + 辅助脚本**：agent 按它通过 SSH 分阶段构建、分流、验证整条链路，
每完成一个阶段先验证再继续。它沉淀了那些一旦踩中就变成"线路不通"的真实坑点——IP 协议族可达性、出站强制
走 IPv4、多个 IP 其实是同一台落地机、MTU 黑洞、过期的 MASQUERADE 等。

### 仓库内容

| 路径 | 用途 |
|------|------|
| `SKILL.md` | skill 入口——何时使用、构建流程 |
| `references/architecture.md` | 决策树：单出口 vs 多出口、按 UUID 把一个入口分流到多条线 |
| `references/pitfalls.md` | 那些最难排查的故障模式及其修复 |
| `references/verification.md` | 如何在进入下一阶段前证明当前阶段可用 |
| `references/lines-spec.md` | 驱动配置 / 验证 / 客户端链接生成的那份小 JSON |
| `scripts/gen_xray_relay_config.py` | 由 spec 生成 xray 中转 inbound/routing 配置 |
| `scripts/gen_client_links.py` | 由 spec 生成 VLESS 客户端链接 / 二维码 |
| `scripts/verify_egress.py` | 绑定每个隧道源 IP，确认它实际落到的公网出口 |
| `assets/templates/*.conf` | 中转和落地两端的 WireGuard `wg0.conf` 模板 |

### 安装

clone 到你的 Claude Code skills 目录：

```bash
git clone https://github.com/superchaospc/reality-wireguard-relay \
  ~/.claude/skills/reality-wireguard-relay
```

这样 **Claude Code** 就能用了。想在 **Codex** 里也能用，再跑一次自带的安装脚本即可——CC 和 Codex
用同一种 `SKILL.md` 格式，一份副本两边通用，脚本只是把 skill 软链进 Codex 的目录
（`~/.codex/skills`、`~/.agents/skills`）：

```bash
~/.claude/skills/reality-wireguard-relay/install.sh
```

脚本自包含（不依赖其它 skill）、可移植（没装的 agent 自动跳过）、幂等。完成后重开 Codex 会话让它重新扫描。

当你让 agent 搭建 "REALITY 入口 + WireGuard 落地" 的链路时该 skill 会自动触发（例如
"搭中转走 reality 落地走 wireguard"、"多出口 IP 落地"、"vless xhttp reality + wireguard 出口"）。

### 安全声明

**本仓库里所有 IP、UUID、short_id、密钥都是占位示例**——IPv6 用 `2001:db8::/32` 文档保留段，出口 IP 用
`203.0.113.0/24` TEST-NET 段，私钥都是截断的（`UNGj…`）。部署前请自行生成密钥：

```bash
xray uuid                 # 每条线的 UUID
xray x25519               # REALITY 密钥对（一对，全部线路复用）
openssl rand -hex 8       # short_id
openssl rand -hex 4       # path
```

**切勿提交真实的服务器 IP、UUID 或私钥。**

## License

[MIT](LICENSE)
