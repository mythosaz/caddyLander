# caddyLander

**caddyLander** is a lightweight landing portal and **Caddyfile Last Known Good (LKG) manager** designed to sit behind Caddy as a wildcard catch-all. It provides:

- A JSON-backed landing page with theming, icons, grouping, and favicon support
- A password-protected admin UI for editing `content.json`
- A built-in **CodeMirror editor** with two language parsers: JSON for `content.json` and NGINX-style syntax for `Caddyfile`
- A vendored **Caddy** binary used for formatting and validating the uploaded Caddyfile
- Automatic, timestamped backups for both `content.json` and the Caddyfile (last 10 copies kept)

caddyLander gives you a single, safe web surface for both landing content and configuration edits.

---

## How It Works

### Landing Page
- The root page (`/`) renders service links defined in `content.json`.
- Runtime state lives at:

        /var/caddy/content.json

- On first run, if no runtime file exists, the server copies the bundled template from:

        /app/content/content.json

### Admin UI
The admin interface (`/admin`) is protected by HTTP Basic Auth. Set `ADMIN_PASSWORD` (default: `caddyLander`) to control access. Inside the admin page you get two editors backed by CodeMirror:

#### 1. Landing Content Editor
- Retrieves and updates `content.json` via `/api/content` and `/api/upload`.
- Persists changes to the `/var/caddy` shared volume.
- Shows inline schema help and validates JSON client-side before upload.

#### 2. Caddyfile Editor (LKG Manager)
- Reads the live `/config/Caddyfile` via `GET /admin/caddyfile`.
- Saves updates via `POST /admin/caddyfile` using a **safe staged pipeline** powered by the bundled Caddy binary:
  1. Writes to `/tmp/caddyfile.upload`
  2. Formats using `caddy fmt --overwrite`
  3. Validates syntax via `caddy adapt --adapter caddyfile --config /tmp/caddyfile.upload`
  4. Promotes to `/config/Caddyfile`
- Each successful save creates a timestamped backup:

        /config/backup/Caddyfile.old.YYYYMMDD-HHMMSS

- Only the most recent **10 backups** are retained.
- If formatting or validation fails, the operation stops and displays the error. Reload Caddy after a successful save.

This provides a safe, browser-accessible way to view, edit, and recover your Caddy configuration without SSH or manual validation.

---

## JSON Format

`content.json` stays backward compatible while supporting richer landing content. All fields are optional unless marked.

```
{
  "siteTitle": "My Services",          // Landing page heading
  "siteSubtitle": "Homelab Dashboard", // Subheading/tagline
  "theme": "dark|light|auto",          // Auto uses system preference
  "favicon": "/static/favicon.ico",    // Path under /static
  "items": [
    {
      "name": "Example Service",        // Required display name
      "url": "https://example.org",     // Required link
      "desc": "Replace this entry",      // Optional description
      "icon": "🚀",                      // Optional emoji/icon
      "group": "Infrastructure"          // Optional grouping header
    }
  ]
}
```

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

- HTTP Basic Auth gate using `ADMIN_PASSWORD` (default `caddyLander`)
- **CodeMirror editors** for both JSON and NGINX-style Caddyfile syntax
- **Safe staged pipeline** (format → validate → promote)
- **Automatic timestamped LKG backups** (retains last 10)
- **Clear error messages** if formatting or validation fails

This makes caddyLander a convenient and safe single-stop management page for Caddy-based homelab deployments. Reload Caddy after saving the Caddyfile.

---

## Licensing

MIT License — see `LICENSE`.
