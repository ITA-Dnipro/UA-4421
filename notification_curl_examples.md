# Notification System - CURL Examples

## Prerequisites
Make sure the server is running:
```bash
docker compose up
```

## 1. Authentication

### Register a Startup User
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "startup_test",
    "email": "startup_test@example.com",
    "password": "TestPass123!",
    "password2": "TestPass123!",
    "full_name": "Startup Test User",
    "user_type": "startup"
  }'
```

### Register an Investor User
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "investor_test",
    "email": "investor_test@example.com",
    "password": "TestPass123!",
    "password2": "TestPass123!",
    "full_name": "Investor Test User",
    "user_type": "investor"
  }'
```

### Login to Get Token
```bash
# For Startup
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "startup_test@example.com",
    "password": "TestPass123!"
  }'

# For Investor
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "investor_test@example.com",
    "password": "TestPass123!"
  }'
```

Save the `access` token from the response. You'll need it for authenticated requests.

## 2. Create Profiles

### Create Startup Profile
```bash
curl -X POST http://localhost:8000/api/startups/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_STARTUP_TOKEN" \
  -d '{
    "company_name": "Tech Innovators Inc",
    "industry": "Technology",
    "description": "Building the future of AI",
    "website": "https://techinnovators.com"
  }'
```

### Create Investor Profile
```bash
curl -X POST http://localhost:8000/api/investors/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_INVESTOR_TOKEN" \
  -d '{
    "company_name": "Venture Capital Partners",
    "investment_focus": ["Technology", "AI", "SaaS"],
    "description": "Early stage investor"
  }'
```

## 3. Save/Follow a Startup (Required for Notifications)

The investor must save/follow a startup to receive notifications about its projects:

```bash
curl -X POST http://localhost:8000/api/saved-items/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_INVESTOR_TOKEN" \
  -d '{
    "startup_id": "STARTUP_PROFILE_ID"
  }'
```

## 4. Create a Project (Triggers Notification)

This will trigger a `project_created` notification for all investors who saved the startup:

```bash
curl -X POST http://localhost:8000/api/startups/STARTUP_ID/projects/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_STARTUP_TOKEN" \
  -d '{
    "title": "AI Assistant Platform",
    "slug": "ai-assistant-platform",
    "short_description": "Revolutionary AI assistant for businesses",
    "description": "Our AI platform helps businesses automate their customer service...",
    "target_amount": 1000000,
    "status": "idea"
  }'
```

**Expected Notification:**
- Type: `project_created`
- Recipients: All investors who saved the startup
- Event Key Format: `project_created:PROJECT_ID:USER_ID:TIMESTAMP`

## 5. Update Project Status (Triggers Notification)

### Change to Fundraising Status
```bash
curl -X PATCH http://localhost:8000/api/projects/PROJECT_ID/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_STARTUP_TOKEN" \
  -d '{
    "status": "fundraising"
  }'
```

**Expected Notification:**
- Type: `project_status_changed`
- Payload includes: `old_status`, `new_status`, `timestamp`

### Change to Funded Status
```bash
curl -X PATCH http://localhost:8000/api/projects/PROJECT_ID/status/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_STARTUP_TOKEN" \
  -d '{
    "status": "funded",
    "raised_amount": 1000000
  }'
```

## 6. Check Notifications

### List All Notifications (As Investor)
```bash
curl -X GET http://localhost:8000/api/notifications/ \
  -H "Authorization: Bearer YOUR_INVESTOR_TOKEN"
```

**Response Example:**
```json
[
  {
    "id": 1,
    "type": "project_created",
    "project": {
      "id": "uuid",
      "title": "AI Assistant Platform"
    },
    "payload": {
      "project_id": "uuid",
      "title": "AI Assistant Platform",
      "status": "idea",
      "timestamp": "2024-01-10T10:00:00Z"
    },
    "is_read": false,
    "created_at": "2024-01-10T10:00:00Z"
  },
  {
    "id": 2,
    "type": "project_status_changed",
    "project": {
      "id": "uuid",
      "title": "AI Assistant Platform"
    },
    "payload": {
      "project_id": "uuid",
      "old_status": "idea",
      "new_status": "fundraising",
      "timestamp": "2024-01-10T11:00:00Z"
    },
    "is_read": false,
    "created_at": "2024-01-10T11:00:00Z"
  }
]
```

## 7. Mark Notification as Read

```bash
curl -X PATCH http://localhost:8000/api/notifications/NOTIFICATION_ID/read/ \
  -H "Authorization: Bearer YOUR_INVESTOR_TOKEN"
```

Returns: 204 No Content on success

## Testing Idempotency

The notification system ensures idempotency using `event_key`. If you trigger the same event multiple times with the same parameters, only one notification will be created.

### Test Idempotency
1. Create a project
2. Note the notification created
3. Manually trigger the same event again (if possible through admin or by replaying)
4. Check that no duplicate notification is created

## Email Notifications (Stub)

The system also has email notification capabilities (currently stubbed):

```bash
# This would be triggered internally by the system
# Shows in logs when notifications are sent
```

## Monitoring Notifications

### Check Server Logs
To see notification processing in real-time:
```bash
docker compose logs -f backend | grep "notification"
```

### Database Query (if you have DB access)
```sql
-- Check all notifications
SELECT * FROM notifications ORDER BY created_at DESC;

-- Check notifications for specific user
SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC;

-- Check unread notifications
SELECT * FROM notifications WHERE is_read = false;
```

## Common Issues and Solutions

### No Notifications Received
- Verify the investor has saved the startup
- Check that Celery workers are running: `docker compose ps`
- Check logs for any errors: `docker compose logs backend worker`

### Duplicate Notifications
- This shouldn't happen due to event_key uniqueness
- Check that timestamps are being properly generated
- Verify the event_key format includes all required components

### Testing with Multiple Users
You can create multiple investor accounts and have them all save the same startup to test that notifications are sent to all followers when a project event occurs.

## Advanced Testing

### Test Project Lifecycle
```bash
# 1. Create project (status: idea)
# 2. Update to MVP
# 3. Update to Fundraising
# 4. Update to Funded
# 5. Check that each status change creates a notification
```

### Test Notification Batching
The system includes email batching logic (24-hour throttle):
- Multiple notifications for the same project within 24 hours
- Only one email should be sent (check logs)

## Cleanup

To reset the test data:
```bash
# If using Docker
docker compose down
docker compose up --build

# Or reset specific tables
docker compose exec backend python manage.py shell
>>> from notifications.models import Notification
>>> Notification.objects.all().delete()
```