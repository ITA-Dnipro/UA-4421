# Messaging architecture

## Databases

For storing messages we use MongoDB. It has these features:

- **Fast append speed,** which is important for users when messaging.
- The **BSON** format has the human-readable qualities of JSON, while also builds and scans quickly.
- **Flexibility,** allowing to easily integrate new data types, without spending a lot of effort to redesign a rigid database.

Meanwhile, for relational data we use Postgres for reasons such as:

- Compatibility with the **users** database.
- **Notification** handling.

For the channel layer we use Redis.

- requirements
- config

## Websocket routing & authentication approach

// TODO(Andrii): Document authentication approach [#4]
// Future task.

## Message lifecycle

1. Send

   When a message is broadcast, mark status='delivered' for recipients whose sockets acknowledged the message (consumer should send ack).

2. Persist

   When user marks messages read (via mark_read or automatically when viewing),

3. Publish to channel

   update message docs and emit read_receipt via Channels to other participants.

4. Create notification via background worker.

   If the recipient(s) is connected on socket, the message is broadcast-only. If the recipient(s) is offline or not focused, the job to create Notification DB record (Postgres) is enqueued and, optionally, an email/push is sent.

## Scaling & retention strategy

MongoDB
It is a non-relational database, that is designed to be self-contained collections instead. As such, it supports **sharding,** a way to horizontally partition the database without breaking it. To remove bloating, MongoDB also supports **TTL indexes** (Time-to-live indexes), meaning temporary data can be automatically removed by MongoDB. Lastly, when old data can't be removed, Mongo supports **archiving** to increase performance when accessing current and old data.

## Security

Security is achieved by these restrictions.

- Authentication checks

- Message content sanitization

  For v1, there is a keyword blocklist for the profanity filter.

- Limiting attachments

  Attachments are pre-uploaded to an existing POST (/api/uploads/) with the upload_id included in message payload. The server resolves the upload_id and stores the reference in the message document attachments.

  Types and sizes of the attachment are validated server-side; if the attachment does not fit the criteria or is invalid, it gets rejected.

  Attachment URLs are served via signed URLs or public S3 links.

- Reporting and admin escalation

  To flag conversation or message POST /api/conversations/{id}/report/. The report is stored and the admin gets notified.

  The admin has an endpoint to read reports and take actions, such as removing the message or banning the user from messaging.

  // TODO(Sofiia or Andrii): Document escalation path for admin. [#3]
  // Future task.

## Backpressure & rate limiting approach.

Each user has a message send throttle. By default it is 30 messages/min. For first N minutes express-interest/send-message endpoints have a stricter limit. Excessive sending results with the offender getting a 429 code.

// TODO(Sofiia or Andrii): Define N and message send throttle [#2]
// Future task.

// Diagrams (sequence for send/receive, flow for offline notifications).
