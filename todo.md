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

1. **Dynamic placeholders in `content.json`** — Support resolving tokens such as `{thisIP}`, `{theCaddyIP}`, or `{theGatewayIP}`.
2. **Caddyfile-driven content generation** — Allow a `content.json` block that reads from the Caddyfile to populate links.
3. **Admin layout/panel tweak** — Move the admin panel to the side or add a live preview pane.
4. **Theme toggle** — Independent client-based dark/light modes for the landing page and the admin UI.
5. **Easter egg** — Optional BalatroTUI link in `content.json` if the payload stays lightweight.
6. **Logging improvements** - Add a startup MOTD, status, and clear logging of edits/saves/validations/pending-reboots - as well as log levels.
7. **Better versioning** - Go to 20151209.1 type numbering?  Display current version link on admin page if out of date?
8. **favicon replacement** - Panel to replace the favicon.svg and .ico if desired.








