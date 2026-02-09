# Messaging architecture

## Databases

For storing messages we use MongoDB. It has these features:

- **Fast append speed,** which is important for users when messaging.
- The **BSON** format has the human-readable qualities of JSON, while also builds and scans quickly.
- **Flexible metadata** //TODO

Meanwhile, for relational data we use Postgres for reasons such as:

- Compatibility with the **users** database.
- **Notification** handling.

For the channel layer we use Redis.

- requirements
- config

## Websocket routing & authentication approach

JWT, because I'm pretty sure we use JWT. Session cookie otherwise.

## Message lifecycle

send → persist → publish to channel → create notification via background worker.

When a message is broadcast, mark status='delivered' for recipients whose sockets acknowledged the message (consumer should send ack).
When user marks messages read (via mark_read or automatically when viewing), update message docs and emit read_receipt via Channels to other participants.
Ensure state changes persisted and visible via REST APIs (message status fields).

Acknowledgement protocol should be lightweight (client emits ack with message id upon receipt).

## Scaling & retention strategy

MongoDB 
It is a non-relational database, that is designed to be self-contained collections instead. As such, it supports **sharding,** a way to horizontally partition the database without breaking it. To remove bloating, MongoDB also supports **TTL indexes** (Time-to-live indexes), meaning temporary data can be automatically removed by MongoDB.
- archiving

## Security

Security is achieved by these restrictions.

### Auth checks

### Message content sanitization

POST /api/conversations/{id}/report/ to flag conversation or message (store report, notify admin).
Admin endpoint to read reports and take action (remove message, ban user from messaging).

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
