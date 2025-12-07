# caddyLander To-Do

A consolidated backlog for upcoming enhancements on the **next** branch. Items are roughly ordered by priority.

## Core Admin Functionality
1. **Admin Password Gate** — Support configuration via environment variable with a sensible default.
2. **Expanded default `content.json`** — Demonstrate all current features and stay backward compatible while considering additional capabilities.
3. **Improved admin editors** — Replace `<textarea>` fields with a FOSS client-side JSON/YAML editor that includes validation (Svelte-friendly if possible).
4. **Admin UI layout cleanup** — Standardize control positions and spacing, tidy edit boxes, and leave room for upcoming features.
5. **Auto-backup on every save** — Mirror Caddyfile behavior by keeping *N* timestamped `content.json` snapshots.
6. **Rollback picker** — Allow loading previous Caddyfile revisions from `/backup`.
7. **Inline admin help** — Provide concise documentation explaining save/version behavior within the UI.
8. **Static asset drop-zone** — Support `/api/upload/static` with a selectable list and delete option.

## Main Site Enhancements
9. **Default favicon** — Add a default spaceship "lander" favicon via the admin for the main site.
10. **Minimal theming controls** — Allow title, subtitle, favicon, and primary color to be configured via `content.json` (or by uploading to `/static`).
