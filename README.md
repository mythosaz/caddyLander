# caddyLander

caddyLander is a tiny JSON-backed landing portal intended to sit behind Caddy as a wildcard catch-all. It serves a simple landing page plus a lightweight admin editor backed by a JSON file.

## How it works
- The landing page (`/`) renders links defined in `content.json`.
- The admin page (`/admin`) fetches and edits the same JSON file through `/api/content` and `/api/upload`.
- Runtime data lives at `/var/caddy/content.json`. On startup, the server copies the template from `/app/content/content.json` if the runtime file is missing.

### JSON format
`content.json` is expected to contain an object with an `items` array:
```json
{
  "items": [
    {
      "name": "Example Service",
      "url": "https://example.org",
      "desc": "Replace this entry with your own services"
    }
  ]
}
```

### Local run with Docker
Build and run with the VETO mnemonic test port (8386 -> 8080 inside the container):
```bash
docker build -t caddylander .
docker run -p 8386:8080 -v caddylander_data:/var/caddy caddylander
```

### docker-compose example
See `docker-compose.example.yml` for a ready-to-use service definition that mounts a volume at `/var/caddy`. For ad-hoc testing, uncomment the provided `ports` section to map 8386 to 8080 (VETO mnemonic).

### Caddy integration
Configure a wildcard site to reverse-proxy to the container:
```caddyfile
*.example.com {
    reverse_proxy caddylander:8080
}
```
Point Caddy at the running service (compose service name `caddylander` or an equivalent host) so any unmatched subdomains land on the portal.

## Licensing
This project is licensed under the MIT License. See `LICENSE` for details.
