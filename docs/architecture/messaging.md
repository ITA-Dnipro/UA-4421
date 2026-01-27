Why MongoDB for message store (fast append, BSON, flexible metadata) and Postgres for relational data (users, notifications).

Channel layer: Redis (requirements and config).

Websocket routing & authentication approach (JWT or session cookie).

Message lifecycle: send → persist → publish to channel → create notification via background worker.

Scaling & retention strategy (sharding, TTL indexes in Mongo, archiving).

Security (auth checks, sanitize message content, limit attachments).

Backpressure & rate limiting approach.

// Diagrams (sequence for send/receive, flow for offline notifications).
