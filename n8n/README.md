# EmailBison Reply Notifications via n8n + Slack

Automatically forward replies from your EmailBison cold email campaigns to a Slack channel. The n8n workflow polls the EmailBison API every 5 minutes and posts a rich notification for each new reply.

## Prerequisites

| What | How to get it |
|------|--------------|
| **n8n instance** | Self-hosted via Docker (see below) or [n8n.cloud](https://n8n.cloud) |
| **EmailBison API Token** | EmailBison dashboard → Settings → Developer API → New API Token |
| **Slack Incoming Webhook URL** | [Create a Slack App](https://api.slack.com/apps) → Incoming Webhooks → Add to Workspace → Copy URL |

## 1. Start n8n

If you don't have n8n running yet, the quickest way is Docker:

```bash
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n
```

Then open `http://localhost:5678` in your browser and create an account.

For persistent production use, see the [n8n self-hosting docs](https://docs.n8n.io/hosting/).

## 2. Create the EmailBison credential in n8n

1. In n8n, go to **Settings → Credentials → Add Credential**
2. Search for **Header Auth**
3. Configure:
   - **Name:** `EmailBison API Token`
   - **Header Name:** `Authorization`
   - **Header Value:** `Bearer <your_emailbison_api_token>`
4. Save

## 3. Set environment variables in n8n

The workflow uses two environment variables. Set them in n8n under **Settings → Variables**, or pass them as environment variables to the n8n Docker container:

| Variable | Value |
|----------|-------|
| `EMAILBISON_BASE_URL` | `https://dedi.emailbison.com` (optional — hardcoded in workflow as fallback) |
| `SLACK_WEBHOOK_URL` | Your Slack Incoming Webhook URL (e.g. `https://hooks.slack.com/services/T.../B.../xxx`) |

If using Docker, pass them at startup:

```bash
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T.../B.../xxx" \
  n8nio/n8n
```

## 4. Import the workflow

1. In n8n, go to **Workflows → Import from File**
2. Select `n8n/workflows/emailbison-reply-slack-notification.json` from this repo
3. Open the imported workflow
4. Click the **Fetch Replies** node → verify the `EmailBison API Token` credential is linked
5. Click the **Post to Slack** node → verify the URL field shows your Slack webhook

## 5. Test the workflow

Before activating the schedule:

1. Click **Execute Workflow** (manual run)
2. The **first run** initializes the deduplication state — it records all existing replies but sends nothing to Slack. This prevents flooding your channel with historical replies.
3. Click **Execute Workflow** again — any existing replies should now appear as "new" and post to Slack
4. Click **Execute Workflow** a third time — no duplicates should be sent

## 6. Activate

Toggle the workflow to **Active** in the top-right corner. It will now poll EmailBison every 5 minutes and notify Slack of new replies automatically.

## Workflow architecture

```
[Schedule Trigger]     Fires every 5 minutes
       ↓
[Fetch Replies]        GET /api/replies with Bearer token auth
       ↓
[Filter New Replies]   JavaScript dedup using static data (timestamp + ID tracking)
       ↓
[Has New Replies?]     IF node — routes to Slack only if new replies exist
       ↓
[Post to Slack]        POST to Incoming Webhook with Block Kit message
```

## Slack notification format

Each notification includes:
- **Lead:** name, email, company
- **Campaign:** name
- **Reply:** first 300 characters of the reply body
- **View in EmailBison** button linking to the campaign

## Troubleshooting

**No Slack messages after activation:**
- Run the workflow manually and inspect each node's output
- Check that the EmailBison API returns replies (the Fetch Replies node output should show data)
- Verify your Slack webhook URL is correct: `curl -X POST -H 'Content-Type: application/json' -d '{"text":"Test"}' $SLACK_WEBHOOK_URL`

**Duplicate notifications after re-import:**
- Workflow static data (dedup state) is lost when a workflow is deleted. After re-importing, the first manual run will re-initialize the state silently.

**Field mapping issues:**
- The EmailBison API response structure may vary. If Slack notifications show "N/A" or "Unknown" for fields, inspect the Fetch Replies node output and update the field paths in the Filter New Replies code node.
- Common field variations: `reply.lead.first_name` vs `reply.first_name`, `reply.body` vs `reply.message`
