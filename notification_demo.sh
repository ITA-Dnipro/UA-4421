#!/bin/bash

# Notification System Demonstration Script
# This script shows how notifications are created in the startup gateway system

BASE_URL="http://localhost:8000"
CONTENT_TYPE="Content-Type: application/json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}Notification System Demonstration${NC}"
echo -e "${BLUE}=====================================${NC}\n"

# ========================================
# STEP 1: Create Users (Startup & Investor)
# ========================================
echo -e "${YELLOW}Step 1: Creating users...${NC}"

# Register startup user
echo -e "${GREEN}Creating startup user...${NC}"
curl -X POST "$BASE_URL/api/auth/register/" \
  -H "$CONTENT_TYPE" \
  -d '{
    "username": "startup_demo",
    "email": "startup@demo.com",
    "password": "DemoPass123!",
    "password2": "DemoPass123!",
    "full_name": "Startup Demo User",
    "user_type": "startup"
  }' | python -m json.tool

# Register investor user
echo -e "${GREEN}Creating investor user...${NC}"
curl -X POST "$BASE_URL/api/auth/register/" \
  -H "$CONTENT_TYPE" \
  -d '{
    "username": "investor_demo",
    "email": "investor@demo.com",
    "password": "DemoPass123!",
    "password2": "DemoPass123!",
    "full_name": "Investor Demo User",
    "user_type": "investor"
  }' | python -m json.tool

echo -e "\n${YELLOW}Step 2: Logging in to get authentication tokens...${NC}"

# Login as startup
echo -e "${GREEN}Getting startup auth token...${NC}"
STARTUP_TOKEN=$(curl -s -X POST "$BASE_URL/api/token/" \
  -H "$CONTENT_TYPE" \
  -d '{
    "email": "startup@demo.com",
    "password": "DemoPass123!"
  }' | python -c "import sys, json; print(json.load(sys.stdin)['access'])")

echo "Startup token: ${STARTUP_TOKEN:0:20}..."

# Login as investor
echo -e "${GREEN}Getting investor auth token...${NC}"
INVESTOR_TOKEN=$(curl -s -X POST "$BASE_URL/api/token/" \
  -H "$CONTENT_TYPE" \
  -d '{
    "email": "investor@demo.com",
    "password": "DemoPass123!"
  }' | python -c "import sys, json; print(json.load(sys.stdin)['access'])")

echo "Investor token: ${INVESTOR_TOKEN:0:20}..."

# ========================================
# STEP 3: Create Startup Profile
# ========================================
echo -e "\n${YELLOW}Step 3: Creating startup profile...${NC}"

STARTUP_PROFILE_ID=$(curl -s -X POST "$BASE_URL/api/startups/" \
  -H "$CONTENT_TYPE" \
  -H "Authorization: Bearer $STARTUP_TOKEN" \
  -d '{
    "company_name": "Demo Tech Startup",
    "industry": "Technology",
    "description": "An innovative tech startup",
    "website": "https://demo-startup.com"
  }' | python -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "Created startup profile with ID: $STARTUP_PROFILE_ID"

# ========================================
# STEP 4: Create Investor Profile
# ========================================
echo -e "\n${YELLOW}Step 4: Creating investor profile...${NC}"

INVESTOR_PROFILE_ID=$(curl -s -X POST "$BASE_URL/api/investors/" \
  -H "$CONTENT_TYPE" \
  -H "Authorization: Bearer $INVESTOR_TOKEN" \
  -d '{
    "company_name": "Demo Ventures",
    "investment_focus": ["Technology", "SaaS"],
    "description": "Leading venture capital firm"
  }' | python -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "Created investor profile with ID: $INVESTOR_PROFILE_ID"

# ========================================
# STEP 5: Investor Saves/Follows Startup
# ========================================
echo -e "\n${YELLOW}Step 5: Investor saves the startup (to receive notifications)...${NC}"

curl -X POST "$BASE_URL/api/saved-items/" \
  -H "$CONTENT_TYPE" \
  -H "Authorization: Bearer $INVESTOR_TOKEN" \
  -d "{
    \"startup_id\": \"$STARTUP_PROFILE_ID\"
  }" | python -m json.tool

# ========================================
# STEP 6: Create Project (Triggers Notification)
# ========================================
echo -e "\n${YELLOW}Step 6: Creating a project (this triggers 'project_created' notification)...${NC}"
echo -e "${RED}⚡ This action triggers a notification for investors who saved the startup!${NC}"

PROJECT_ID=$(curl -s -X POST "$BASE_URL/api/startups/$STARTUP_PROFILE_ID/projects/" \
  -H "$CONTENT_TYPE" \
  -H "Authorization: Bearer $STARTUP_TOKEN" \
  -d '{
    "title": "Revolutionary AI Platform",
    "slug": "revolutionary-ai-platform",
    "short_description": "AI-powered solution for businesses",
    "description": "A comprehensive AI platform that revolutionizes business operations",
    "target_amount": 500000,
    "status": "idea"
  }' | python -c "import sys, json; print(json.load(sys.stdin)['id'])")

echo "Created project with ID: $PROJECT_ID"
echo -e "${GREEN}✓ 'project_created' notification sent to investors${NC}"

# Wait for async processing
echo "Waiting for async notification processing..."
sleep 2

# ========================================
# STEP 7: Check Notifications (as Investor)
# ========================================
echo -e "\n${YELLOW}Step 7: Checking notifications for investor...${NC}"

echo -e "${GREEN}Fetching investor's notifications:${NC}"
curl -X GET "$BASE_URL/api/notifications/" \
  -H "Authorization: Bearer $INVESTOR_TOKEN" | python -m json.tool

# ========================================
# STEP 8: Update Project Status (Triggers Another Notification)
# ========================================
echo -e "\n${YELLOW}Step 8: Updating project status to 'fundraising'...${NC}"
echo -e "${RED}⚡ This triggers 'project_status_changed' notification!${NC}"

curl -X PATCH "$BASE_URL/api/projects/$PROJECT_ID/" \
  -H "$CONTENT_TYPE" \
  -H "Authorization: Bearer $STARTUP_TOKEN" \
  -d '{
    "status": "fundraising"
  }' | python -m json.tool

echo -e "${GREEN}✓ 'project_status_changed' notification sent to investors${NC}"

# Wait for async processing
sleep 2

# ========================================
# STEP 9: Check Updated Notifications
# ========================================
echo -e "\n${YELLOW}Step 9: Checking updated notifications...${NC}"

NOTIFICATIONS=$(curl -s -X GET "$BASE_URL/api/notifications/" \
  -H "Authorization: Bearer $INVESTOR_TOKEN")

echo "$NOTIFICATIONS" | python -m json.tool

# Get first notification ID for marking as read
NOTIFICATION_ID=$(echo "$NOTIFICATIONS" | python -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id']) if data else print('None')")

# ========================================
# STEP 10: Mark Notification as Read
# ========================================
if [ "$NOTIFICATION_ID" != "None" ]; then
  echo -e "\n${YELLOW}Step 10: Marking notification as read...${NC}"
  
  curl -X PATCH "$BASE_URL/api/notifications/$NOTIFICATION_ID/read/" \
    -H "Authorization: Bearer $INVESTOR_TOKEN"
  
  echo -e "\n${GREEN}✓ Notification marked as read${NC}"
fi

# ========================================
# STEP 11: Update to 'funded' Status
# ========================================
echo -e "\n${YELLOW}Step 11: Updating project status to 'funded'...${NC}"
echo -e "${RED}⚡ This triggers another 'project_status_changed' notification!${NC}"

curl -X PATCH "$BASE_URL/api/projects/$PROJECT_ID/status/" \
  -H "$CONTENT_TYPE" \
  -H "Authorization: Bearer $STARTUP_TOKEN" \
  -d '{
    "status": "funded",
    "raised_amount": 500000
  }' | python -m json.tool

# Wait for async processing
sleep 2

# ========================================
# STEP 12: Final Notification Check
# ========================================
echo -e "\n${YELLOW}Step 12: Final check of all notifications...${NC}"

curl -X GET "$BASE_URL/api/notifications/" \
  -H "Authorization: Bearer $INVESTOR_TOKEN" | python -m json.tool

# ========================================
# SUMMARY
# ========================================
echo -e "\n${BLUE}=====================================${NC}"
echo -e "${BLUE}Summary of Notification Triggers:${NC}"
echo -e "${BLUE}=====================================${NC}"
echo -e "${GREEN}1. Project Creation:${NC} Sends 'project_created' notification"
echo -e "${GREEN}2. Status → Fundraising:${NC} Sends 'project_status_changed' notification"
echo -e "${GREEN}3. Status → Funded:${NC} Sends 'project_status_changed' notification"
echo -e "\n${YELLOW}Key Points:${NC}"
echo -e "• Notifications are sent only to investors who have saved the startup"
echo -e "• Each notification has a unique event_key for idempotency"
echo -e "• Notifications include timestamps to prevent duplicates"
echo -e "• Notifications can be marked as read via the API"
echo -e "\n${BLUE}=====================================${NC}"