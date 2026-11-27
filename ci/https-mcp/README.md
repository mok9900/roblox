# HTTPS MCP fallback (initial read-only rollout)

This is a separate transport experiment. Existing Roblox Studio authentication, official Studio MCP launcher and OpenAI Secure MCP Tunnel workflows remain unchanged.

## Verified
- GitHub-hosted Windows regression: [45962616051](https://github.com/mok9900/roblox/actions/runs/45962616051), all five tests passed.
- Loopback HTTP JSON-RPC, synthetic stdio MCP exchange, exact local fixture matching, signed JWT verification (issuer, audience, email, expiry, signature), secret exclusion and fail-closed tool allowlisting tested.
- Synthetic fixture results are NOT actual Roblox Studio or ChatGPT connectivity.

## Deployment gates
1. Cloudflare account owns the active xoxgroup.store zone. Access organization and apps API returned HTTP 403 access.api.error.not_enabled. Owner must enable Access/Zero Trust using the Cloudflare dashboard, without selecting a paid plan unless explicitly authorized.
2. Create a dedicated named tunnel and new unused hostname (proposed roblox-mcp.xoxgroup.store); do not alter existing hostaster or aster-search-lab tunnels. Configure its ingress to loopback http://127.0.0.1:18765 with a catch-all 404. Do not publish DNS or start the tunnel until OAuth protection and origin JWT verification are configured.
3. Create a self-hosted Access MCP application with Managed OAuth, restricted to the authorized owner; configure ChatGPT-compatible redirect URIs according to current official docs. Verify resource metadata and JWT forwarding. Keep the tunnel token in GitHub Actions secrets; never print or commit it.
4. Bridge environment requires CF_ACCESS_ISSUER (HTTPS team domain), CF_ACCESS_AUD, CF_ACCESS_ALLOWED_EMAIL and ROBLOX_MCP_PUBLIC_ORIGIN. Configure secrets/variables through the GitHub settings UI; no credentials in this repository. Install PyJWT[crypto] and use existing signed official Studio setup, verified local Baseplate and official mcp.bat. Production setup must preserve hosted-only and single-run concurrency, and not depend on an unverified alternative launcher.
5. Perform unauthenticated negative test before the OAuth-authorized smoke test. Verify the real endpoint, then connect ChatGPT with OAuth; use Plugin Creator only for a supported remote endpoint, not to bypass its authorization flow. The only exposed tool at this stage is verify_ci_studio. Success requires its actual official MCP call to report exactly one local fixture. Do not enable edit tools or expose a cloud place until separately authorized and verified.
6. GitHub-hosted jobs expire; this is not proof of 24/7 availability.

References:
- https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/secure-mcp-servers/
- https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/managed-oauth/
- https://developers.openai.com/plugins/build/auth
