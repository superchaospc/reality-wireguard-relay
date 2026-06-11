# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] — 2026-06-11

### Changed
- README intro (EN + 中文) reworded to match the repo description: landing egress is
  via **SNAT** and can be split across **multiple exit IPs**, and the project is framed
  as a **playbook + helper scripts** (not a one-click installer).

## [1.1.0] — 2026-06-11

### Added
- **`install.sh`** — self-contained one-shot installer that makes the skill usable by
  **both Claude Code and Codex**. It symlinks the skill into each installed agent's skill
  dir (`~/.codex/skills`, `~/.agents/skills`); Claude Code and Codex share the same
  `SKILL.md` format, so one copy serves both. Portable (uninstalled agents are skipped),
  idempotent, never overwrites a real directory.
- README install sections (EN + 中文) now cover Codex, plus a Codex skill badge.

## [1.0.0] — 2026-06-11

### Added
- Initial public release: the REALITY-front + WireGuard-backhaul deployment playbook —
  `SKILL.md`, `references/` (architecture, pitfalls, verification, lines-spec), helper
  scripts (`gen_xray_relay_config.py`, `gen_client_links.py`, `verify_egress.py`), and
  WireGuard `wg0.conf` templates. All IPs/UUIDs/keys are placeholder examples.

[1.1.1]: https://github.com/superchaospc/reality-wireguard-relay/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/superchaospc/reality-wireguard-relay/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/superchaospc/reality-wireguard-relay/releases/tag/v1.0.0
