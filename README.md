# caddyLander

**caddyLander** is a lightweight landing portal and **Caddyfile Last Known Good (LKG) manager** designed to sit behind Caddy as a wildcard catch-all. It provides:

- A simple, JSON-backed landing page  
- An admin UI for editing `content.json`  
- A built-in **Caddyfile editor with automatic versioned backups**  

caddyLander gives you a single web surface for both landing content and safe configuration edits.

---

## How It Works

### Landing Page
- The root page (`/`) renders service links defined in `content.json`.
- Runtime state lives at:

        /var/caddy/content.json

- On first run, if no runtime file exists, the server copies the bundled template from:

        /app/content/content.json

### Admin UI
The admin interface (`/admin`) provides two editors:

#### 1. Landing Content Editor
- Retrieves and updates `content.json` via `/api/content` and `/api/upload`.
- Persists changes to the `/var/caddy` shared volume.

#### 2. Caddyfile Editor (LKG Manager)
- Reads the live `/config/Caddyfile` via `GET /admin/caddyfile`.
- Saves updates via `POST /admin/caddyfile`.
- Each save creates a timestamped backup:

        /config/backup/Caddyfile.old.YYYYMMDD-HHMMSS

- Only the most recent **10 backups** are retained.
- No validation or reload is performed automatically.
- After saving, the UI displays a **“Restart Caddy Required”** notice.

This provides a simple, browser-accessible way to view, edit, and recover your Caddy configuration without SSH.

---

## JSON Format

Expected structure:

        {
          "items": [
            {
              "name": "Example Service",
              "url": "https://example.org",
              "desc": "Replace this entry with your own services"
            }
          ]
        }

---

## Local Run with Docker

Use the VETO mnemonic port (8386 → 8080):

        docker build -t caddylander .
        docker run -p 8386:8080 -v caddylander_data:/var/caddy caddylander

---

## docker-compose Example

See `docker-compose.example.yml` for a full stack using the published image `mythosaz/caddylander:main`.

Before deploying:

        docker volume create caddy_var
        docker volume create caddy_config

These volumes store:

- Landing page data: `/var/caddy`
- Live Caddy configuration: `/config`

The compose file includes an optional local debug port (8386).

---

## Deployment Notes

- caddyLander must run on the **same Docker or LAN network** as your Caddy container so it can be referenced in `reverse_proxy` directives.
- Mount the **same configuration directory** that Caddy uses into caddyLander at `/config` so the admin UI edits the live Caddyfile.
- Mount `caddy_var` into both Caddy and caddyLander if you want shared JSON state between the landing page and your reverse proxy environment.

---

## Caddy Integration

Wildcard example:

        *.example.com {
            reverse_proxy caddylander:8080
        }

When running under Compose, reference the service name (`caddylander`) or use a LAN IP if running on MACVLAN/QNAP networks.

For best results:
- Load specific service routes first  
- Place the wildcard route last  
- Let caddyLander handle everything unmatched  

---

## Admin UI Summary

Includes:

- **Landing content editor** (JSON-based)
- **Caddyfile Editor** (view + edit + save)
- **Automatic timestamped LKG backups** (retains last 10)
- **Restart notice** after saving

This makes caddyLander a convenient and safe single-stop management page for Caddy-based homelab deployments.

---

## Licensing

MIT License — see `LICENSE`.
