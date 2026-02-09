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

Security is achieved by these restrictions

### auth checks

### sanitize message content

### Limiting attachments

Attachments are pre-uploaded to an existing POST (/api/uploads/) with the upload_id included in message payload. The server resolves the upload_id and stores the reference in the message document attachments.

Types and sizes of the attachment are validated server-side; if the attachment does not fit the criteria or is invalid, it gets rejected.

Attachment URLs are served via signed URLs or public S3 links.

### Admin escalation

// TODO(Sofiia or Andrii): Document escalation path for admin. [#3]
// Future task: don't overextend scope.

## Backpressure & rate limiting approach.

// Diagrams (sequence for send/receive, flow for offline notifications).
