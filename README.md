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

**caddyLander** is a web-based Caddyfile editor and landing page generator that shares volumes with your Caddy container. You edit your Caddyfile in a browser, it validates before saving, and you get a simple service dashboard as a bonus.

---

## The Core Concept

caddyLander needs access to **two directories** that Caddy already uses:

| Volume Mount | What Lives There | Who Uses It |
|--------------|------------------|-------------|
| `/config` | Your live `Caddyfile` | Caddy reads it; caddyLander edits it |
| `/var/caddy` | `content.json` (landing page data) | caddyLander reads/writes it |

That's it. caddyLander is a sidecar that edits Caddy's config files through a shared volume.

---

## What You Get

**1. A Caddyfile Editor** (`/admin`)
- Browser-based editing with syntax highlighting
- Validates syntax before saving (uses a vendored Caddy binary)
- Auto-formats on save
- Keeps timestamped backups (last 10)
- If validation fails, nothing gets written—your running config stays safe

**2. A Landing Page** (`/`)
- Renders links from `content.json`
- Supports grouping, icons, descriptions, theming
- Editable from the same admin UI

**3. Password Protection**
- Admin UI requires HTTP Basic Auth
- Set via `ADMIN_PASSWORD` environment variable (default: `caddyLander`)

---

## Volume Setup

You likely already have `caddy_config` and `caddy_data` from your Caddy install. You'll need to add one volume for landing page state:

```bash
docker volume create caddy_var
```

Then mount the shared volumes in both containers:

```yaml
# Your existing Caddy container — add caddy_var
volumes:
  - caddy_config:/config
  - caddy_data:/data
  - caddy_var:/var/caddy    # ← add this

# caddyLander container — shares config and var
volumes:
  - caddy_config:/config    # caddyLander edits your Caddyfile here
  - caddy_var:/var/caddy    # landing page content.json lives here
```

caddyLander writes to `/config/Caddyfile`. Caddy reads from `/config/Caddyfile`. Same file.

---

## Caddy Integration

Point your wildcard catch-all at caddyLander:

```
*.example.com {
    reverse_proxy caddylander:8080
}
```

Load order matters—put specific routes first, wildcard last. Everything unmatched lands on your dashboard.

**Optional:** Direct admin access without the landing page:

```
caddylander.example.com {
    reverse_proxy caddylander:8080
    handle_path / {
        redir /admin.html
    }
}
```

---

## docker-compose Example

```yaml
services:
  caddy:
    image: caddy:latest
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - caddy_config:/config
      - caddy_data:/data
      - caddy_var:/var/caddy    # shared with caddyLander
    networks:
      - caddy_net

  caddylander:
    image: mythosaz/caddylander:main
    restart: unless-stopped
    environment:
      - ADMIN_PASSWORD=YourSecurePassword
    volumes:
      - caddy_config:/config    # edits your Caddyfile
      - caddy_var:/var/caddy    # landing page state
    networks:
      - caddy_net
    # Optional debug port:
    # ports:
    #   - "8386:8080"

volumes:
  caddy_config:
    external: true    # assuming these already exist
  caddy_data:
    external: true
  caddy_var:          # create this one: docker volume create caddy_var

networks:
  caddy_net:
```

---

## The Save Pipeline

When you save a Caddyfile edit:

1. Written to `/tmp/caddyfile.upload`
2. Formatted via `caddy fmt --overwrite`
3. Validated via `caddy adapt`
4. **If valid:** Promoted to `/config/Caddyfile`, backup created
5. **If invalid:** Error displayed, nothing written

Backups go to `/config/backup/Caddyfile.old.YYYYMMDD-HHMMSS`. Last 10 kept.

**You still need to reload Caddy** after saving. caddyLander edits the file; Caddy reads it on reload.

---

## content.json Format

All fields optional except `name` and `url` on items:

```json
{
  "siteTitle": "My Services",
  "siteSubtitle": "Homelab Dashboard",
  "theme": "dark",
  "favicon": "/static/favicon.ico",
  "items": [
    {
      "name": "Service Name",
      "url": "https://service.example.com",
      "desc": "Optional description",
      "icon": "🚀",
      "group": "Infrastructure"
    }
  ]
}
```

On first run, if `/var/caddy/content.json` doesn't exist, a template is copied from the container.

---

## Quick Start (Local Testing)

```bash
docker build -t caddylander .
docker run -p 8386:8080 -v caddylander_data:/var/caddy caddylander
```

Visit `http://localhost:8386` for the landing page, `http://localhost:8386/admin` for the editor.

---

## Screenshots

**Admin Portal:**

<img width="1234" alt="Admin interface showing Caddyfile and content editors" src="https://github.com/user-attachments/assets/57c65fd2-26d4-4f34-a7d8-1cbd8a6df4c9" />

**Landing Page:**

<img width="1243" alt="Example landing page with grouped services" src="https://github.com/user-attachments/assets/a69954dd-8970-4f33-8f76-137a7c26cbe2" />

---

## License

MIT — see `LICENSE`.
