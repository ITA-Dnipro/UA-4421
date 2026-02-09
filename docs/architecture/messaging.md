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

Security is achieved by these restrictions.

### Auth checks

### Message content sanitization

### Limiting attachments

Attachments are pre-uploaded to an existing POST (/api/uploads/) with the upload_id included in message payload. The server resolves the upload_id and stores the reference in the message document attachments.

Types and sizes of the attachment are validated server-side; if the attachment does not fit the criteria or is invalid, it gets rejected.

Attachment URLs are served via signed URLs or public S3 links.

### Reporting and admin escalation

To flag conversation or message POST /api/conversations/{id}/report/. The report is stored and the admin gets notified.

The admin has an endpoint to read reports and take actions, such as removing the message or banning the user from messaging.

// TODO(Sofiia or Andrii): Document escalation path for admin. [#3]
// Future task.

## Backpressure & rate limiting approach.

Each user has a message send throttle. By default it is 30 messages/min. For first N minutes express-interest/send-message endpoints have a stricter limit. Excessive sending results with the offender getting a 429 code.

// TODO(Sofiia or Andrii): Define N and message send throttle [#2]
// Future task.

// Diagrams (sequence for send/receive, flow for offline notifications).
