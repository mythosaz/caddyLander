# caddyLander To-Do

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

1. **Dynamic placeholders in `content.json`** — Allow resolving tokens such as `{thisIP}`, `{caddyIP}`, `{gatewayIP}`, or small templated values.
2. **Caddyfile-driven content generation** — Optional block in `content.json` that auto-populates services based on the active Caddyfile.
3. **Admin layout improvements** — Consider a sidebar layout or a live preview pane for faster iteration.
4. **Theme toggle** — Independent dark/light mode selector for both the landing page and the admin UI.
5. **Easter egg** — Optional BalatroTUI launch link if footprint remains lightweight.
6. **Logging improvements** — Add a startup MOTD, version banner, structured logging for edits/saves/validations/restarts, and log-level selection.
7. **Versioning polish** — Move to `YYYYMMDD.X` builds; optionally display “an update is available” in the admin UI when Docker Hub has a newer tag.
8. **Favicon management** — Add a panel to upload/replace the `favicon.svg` and `favicon.ico` assets from the browser.
