Restore Password – Security & Deployment Guidelines
1. Token TTL & Expiry Policy
 Recommended Token TTL
 | Token Type                    | Recommended TTL | Notes                   |
| ----------------------------- | --------------- | ----------------------- |
| Password Reset Token          | **1 hour**      | Short-lived, single use |
| Email verification (optional) | 24 hours        | If separate flow        |
| Auth Access Token             | 15–30 min       | If JWT-based auth       |
| Refresh Token                 | 7–30 days       | Rotate on use           |
Reset Token Rules

Token MUST be:

    Cryptographically secure (min 256-bit entropy)

    Single-use

    Invalidated after successful reset

Token expires automatically after 1 hour

On new reset request:

    Either invalidate previous token

    Or allow only latest token to remain valid

Expiry Handling

    Expired token returns:

        400 Bad Request

        Generic message: "Invalid or expired token"

Never expose whether:

    Token exists

    Email exists   
2. Throttling Policy (Rate Limiting)
Recommended Limits
| Scope            | Limit                     |
| ---------------- | ------------------------- |
| Per Email        | 5 requests/hour           |
| Per IP           | 10 requests/hour          |
| Global threshold | Alert if >100 resets/hour |

Behavior on Exceed
    Return HTTP 429 Too Many Requests

    Generic response:
     "If account exists, email will be sent."

Implementation Options

    Redis-based rate limiting

    API Gateway rate limiting

    Reverse proxy (NGINX) rules
3. Token Storage Strategy
Option A – Stateful (Recommended for most apps)

Store token hash in DB

Schema example:
password_reset_tokens
- id
- user_id
- token_hash
- expires_at
- used_at
- created_at
Pros:

    Easy revocation

    Easy monitoring

    Can track usage

    More secure for high-risk apps

Cons:

    DB lookup required
Option B – Stateless (JWT-based reset token)
Pros:

    No DB lookup

    Simpler infra

Cons:

    Harder to revoke

    Cannot easily track usage

    Must blacklist if compromised

 Recommendation:
Use stateful tokens with hashed storage for production.
4. Token Generation Best Practices

    Use cryptographically secure random generator

    Minimum length: 32 bytes

    Store only SHA-256 hash in DB

    Never store raw token

Example flow:

    Generate random token

    Send raw token via email

    Store hash(token) in DB

    On verify → hash input token → compare
5. Email Provider Security

    Store provider secrets in:

        Environment variables

        Secret manager (Vault, AWS Secrets Manager, etc.)

    Never commit:

        SMTP passwords

        API keys

    Enable:

        SPF

        DKIM

        DMARC

Rotate secrets every 90 days.
6. CORS & CSRF Considerations
If using JWT in Authorization header

    CSRF risk: LOW

    CORS:

        Allow only trusted frontend domains

        Disallow * in production
If using cookies for auth

    Enable:

        HttpOnly

        Secure

        SameSite=Lax or Strict

    Enable CSRF protection:

        Double submit cookie

        CSRF token validation
7. Monitoring & Alerting
Metrics to Expose
| Metric                       | Alert Threshold |
| ---------------------------- | --------------- |
| Reset requests per minute    | >20/min         |
| Reset per email              | >5/hour         |
| Failed token confirmations   | >10/hour        |
| Expired token usage attempts | >15/hour        |
| 429 responses                | Spike detection |
Logs to Capture

    Email hash (not raw email)

    IP address

    User agent

    Timestamp

    Result (success / expired / invalid / rate_limited)
8. Abuse Detection Signals

Alert if:

    Many reset attempts for one email

    Many reset attempts from one IP

    High invalid token attempts

    Spike in expired token confirmations

    Reset + login failures pattern
9. Incident Runbook
Scenario A – Token brute force suspected

    Increase rate limiting temporarily

    Invalidate all active reset tokens

    Review logs for affected emails

    Notify security team

    Consider temporary CAPTCHA

Scenario B – Email flooding attack

    Enable stricter per-email throttling

    Add CAPTCHA to reset request

    Notify email provider if rate limits triggered

    Monitor IP addresses

    Temporarily block abusive IPs

Scenario C – Token database leak

    Immediately:

        Revoke all reset tokens

    Rotate:

        Email provider secrets

        App secrets

    Force password reset for impacted users

    Audit logs

    Conduct security review

Scenario D – Compromised Email Provider

    Disable provider integration

    otate API keys

    Enable backup provider

    Audit outbound mail logs
10. Production Hardening Checklist

    Reset tokens hashed in DB

    Single-use enforced

    TTL set to 1 hour

    Rate limiting enabled

    Monitoring configured

    Alert thresholds set

    Secrets stored securely

    CORS restricted

    CSRF enabled (if cookies)

    Incident runbook reviewed by team
11. Recommended HTTP Responses
| Case                  | Status | Message                          |
| --------------------- | ------ | -------------------------------- |
| Request accepted      | 200    | "If account exists, email sent." |
| Invalid/expired token | 400    | "Invalid or expired token."      |
| Rate limited          | 429    | "Too many requests. Try later."  |
| Successful reset      | 200    | "Password updated successfully." |
12. Additional Hardening (Optional)

    Add CAPTCHA after 3 failed attempts

    Device fingerprinting

    Geo anomaly detection

    Require recent login re-verification for sensitive changes

Acceptance Criteria
✔ Production-ready recommendations
✔ Clear TTL and throttle policy
✔ Monitoring thresholds defined
✔ Incident response steps documented
✔ Suitable for security review
