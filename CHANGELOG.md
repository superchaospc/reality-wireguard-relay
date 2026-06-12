# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] — 2026-06-12

### Added
- **`scripts/export_links.py`** — turn the `vless://` links and QR codes into shareable
  **PDF / HTML / PNG / Excel** exports. It scans for `vless://` lines, so the
  `all-links.txt` from `gen_client_links.py` (or any pasted link blob) feeds straight in:
  `python3 scripts/export_links.py --input client-links/all-links.txt --out ./exports`.
  Default writes all four formats (per-line QR PNGs, a self-contained HTML gallery, a
  printable PDF, and an XLSX table with embedded QR); each degrades independently if its
  library is missing. Needs `segno reportlab openpyxl pillow`.
- `SKILL.md` — new **Phase 8** documenting the export flow.

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

[1.2.0]: https://github.com/superchaospc/reality-wireguard-relay/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/superchaospc/reality-wireguard-relay/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/superchaospc/reality-wireguard-relay/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/superchaospc/reality-wireguard-relay/releases/tag/v1.0.0
