# caddyLander

[![Docker Pulls](https://img.shields.io/docker/pulls/mythosaz/caddylander)](https://hub.docker.com/r/mythosaz/caddylander)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/mythosaz/caddyLander?style=flat)](https://github.com/mythosaz/caddyLander/stargazers)
![Image Size](https://img.shields.io/docker/image-size/mythosaz/caddylander/main)

<pre>
                       █████     █████            █████                                █████                   
                       ░░███     ░░███            ░░███                                ░░███                    
  ██████   ██████    ███████   ███████  █████ ████ ░███         ██████   ████████    ███████   ██████  ████████ 
 ███░░███ ░░░░░███  ███░░███  ███░░███ ░░███ ░███  ░███        ░░░░░███ ░░███░░███  ███░░███  ███░░███░░███░░███
░███ ░░░   ███████ ░███ ░███ ░███ ░███  ░███ ░███  ░███         ███████  ░███ ░███ ░███ ░███ ░███████  ░███ ░░░ 
░███  ███ ███░░███ ░███ ░███ ░███ ░███  ░███ ░███  ░███      █ ███░░███  ░███ ░███ ░███ ░███ ░███░░░   ░███     
░░██████ ░░████████░░████████░░████████ ░░███████  ███████████░░████████ ████ █████░░████████░░██████  █████    
 ░░░░░░   ░░░░░░░░  ░░░░░░░░  ░░░░░░░░   ░░░░░███ ░░░░░░░░░░░  ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░░░  ░░░░░░  ░░░░░     
                                         ███ ░███                                                               
                                        ░░██████                                                                
                                         ░░░░░░                                                                 
</pre>
**caddyLander** is a lightweight landing portal and **Caddyfile Last Known Good (LKG) manager** designed to sit behind Caddy as a wildcard catch-all. It’s not a CMS — it’s a safe, minimal control surface for your homelab. It provides:

- A JSON-backed landing page with theming, icons, grouping, and favicon support  
- A password-protected admin UI for managing `content.json`  
- A built-in **CodeMirror editor** with JSON and NGINX-style Caddyfile syntax highlighting  
- A vendored **Caddy** binary that formats, validates, and safely stages Caddyfile updates  
- Automatic, timestamped backups of both `content.json` and the Caddyfile (last 10 copies kept)

At its core, caddyLander gives you a **single secure web surface** for both your landing content and a **safe, LKG-protected Caddyfile editing workflow**, without ever touching SSH.


---

Admin Portal:

<img width="1234" height="1745" alt="image" src="https://github.com/user-attachments/assets/57c65fd2-26d4-4f34-a7d8-1cbd8a6df4c9" />


---

A user-configured landing page:

<img width="1243" height="1312" alt="image" src="https://github.com/user-attachments/assets/a69954dd-8970-4f33-8f76-137a7c26cbe2" />


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

Wildcard example (full catch-all):

    *.example.com {
        reverse_proxy caddylander:8080
    }

When running under Compose, reference the service name (`caddylander`) or use a LAN IP if running on MACVLAN/QNAP networks.

For best results:
- Load specific service routes first
- Place the wildcard route last
- Let caddyLander handle everything unmatched


### Optional: Direct Admin Access Without Using the Wildcard Redirect

If you want a dedicated hostname for admin UI only — without sending normal traffic to the landing page — point it at `/admin.html`:

    caddylander.example.com {
        reverse_proxy caddylander:8080

        handle_path / {
            redir /admin.html
        }
    }

This gives you:
- A clean admin-only URL (`https://caddylander.example.com`)
- No wildcard interference
- No general redirect — only `/admin.html` is intentionally exposed


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
