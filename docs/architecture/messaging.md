# Messaging architecture

## Databases

For storing messages we use MongoDB. It has these features:

- **Fast append speed,** which is important for users when messaging.
- The **BSON** format has the human-readable qualities of JSON, while also builds and scans quickly.
- **Flexible metadata** //TODO

Postgres for relational data

- users
- notifications

## Channel layer

Redis

- requirements
- config

## Websocket routing & authentication approach

JWT, because I'm pretty sure we use JWT. Session cookie otherwise.

## Message lifecycle

send → persist → publish to channel → create notification via background worker.

## Scaling & retention strategy

- sharding
- TTL indexes in Mongo
- archiving

## Security

### auth checks

### sanitize message content

### limit attachments

## Backpressure & rate limiting approach.

// Diagrams (sequence for send/receive, flow for offline notifications).
