# Twitter Bot Integration - MVP Plan

## Overview

A polling script that monitors Twitter mentions, analyzes hairlines in attached images, and replies with roasts. Runs in a tmux pane on the existing EC2 instance.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  EC2 tmux session                                               │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  pane 1         │  pane 2         │  pane 3                     │
│  (fastapi)      │  (celery)       │  twitter_bot.py             │
│                 │                 │  (polling loop)             │
└─────────────────┴─────────────────┴─────────────────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │  Twitter API    │
                                    │  (poll mentions)│
                                    └────────┬────────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          ▼                  ▼                  ▼
                    ┌──────────┐      ┌──────────────┐   ┌──────────────┐
                    │ Download │      │ Celery Task  │   │ Post Reply   │
                    │ Image    │      │ (analysis)   │   │ to Tweet     │
                    └──────────┘      └──────────────┘   └──────────────┘
```

## Twitter API Requirements

### Keys Needed (store in AWS Secrets Manager)

Add these to your existing secrets:

```json
{
  "TWITTER_API_KEY": "...",
  "TWITTER_API_SECRET": "...",
  "TWITTER_ACCESS_TOKEN": "...",
  "TWITTER_ACCESS_TOKEN_SECRET": "...",
  "TWITTER_BEARER_TOKEN": "..."
}
```

### API Tier

**Basic tier ($100/month)** - provides:
- 10,000 tweet reads/month
- 1,500 tweets posted/month
- Access to `GET /2/users/:id/mentions` endpoint

This is sufficient for MVP polling.

### Getting Keys

1. Go to https://developer.twitter.com/
2. Create a project and app
3. Enable OAuth 1.0a (for posting replies)
4. Generate all keys above
5. Add to AWS Secrets Manager under existing secret or new `norwood/twitter` secret

## Implementation

### File Structure

```
app/
├── twitter/
│   ├── __init__.py
│   ├── bot.py           # Main polling loop
│   ├── client.py        # Twitter API wrapper
│   └── roast.py         # Roast generation prompt
├── tasks/
│   └── twitter.py       # Celery task for Twitter analysis
```

### Core Components

#### 1. Twitter Client (`app/twitter/client.py`)

Wrapper around tweepy or raw requests:
- `get_mentions(since_id)` - fetch new mentions
- `get_tweet_media(tweet)` - extract image URLs from tweet
- `reply_to_tweet(tweet_id, text)` - post reply

#### 2. Polling Loop (`app/twitter/bot.py`)

```python
# Pseudocode
def main():
    last_seen_id = load_last_seen_id()  # persist to file or redis

    while True:
        mentions = twitter_client.get_mentions(since_id=last_seen_id)

        for mention in mentions:
            if has_image(mention):
                process_mention(mention)
            last_seen_id = max(last_seen_id, mention.id)

        save_last_seen_id(last_seen_id)
        sleep(300)  # 5 minutes
```

#### 3. Celery Task (`app/tasks/twitter.py`)

New task specifically for Twitter - doesn't save to DB or require user_id:

```python
@celery_app.task(bind=True, name="analyze_twitter_image")
def analyze_twitter_image_task(self, image_base64: str, media_type: str) -> dict:
    """Analyze image and return roast text."""
    # Reuse execute_vision_task with Twitter-specific prompt
    # Return roast text instead of full analysis
```

#### 4. Roast Prompt (`app/twitter/roast.py`)

Twitter-specific prompt that generates short, punchy roasts:
- Must be under 280 chars
- More savage than the stoic Marcus Aurelius style
- Include the Norwood stage in the roast

Example output: "Norwood 4 energy right here. Your hairline's in witness protection. 👨‍🦲"

### Polling Script Entry Point

```bash
# Run from project root
python -m app.twitter.bot
```

Or add to Makefile:

```makefile
twitter-bot:
    python -m app.twitter.bot
```

## Flow

1. **Poll** - Every 5 min, hit `GET /2/users/:id/mentions?since_id=X`
2. **Filter** - Skip mentions without images
3. **Download** - Fetch image from Twitter's CDN
4. **Analyze** - Queue `analyze_twitter_image_task.delay(image_b64, media_type)`
5. **Wait** - Poll task result (or use `.get()` with timeout)
6. **Reply** - Post roast as reply to original tweet
7. **Track** - Save `last_seen_id` to avoid reprocessing

## State Persistence

Simple file-based for MVP:

```python
# app/twitter/state.py
STATE_FILE = "/tmp/norwood_twitter_state.json"

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {"last_seen_id": None}

def save_state(state: dict):
    json.dump(state, open(STATE_FILE, "w"))
```

Or use Redis if you want it to survive reboots (you probably have Redis for Celery already).

## Rate Limits & Safety

- **Polling interval**: 5 minutes (288 calls/day = ~8,640/month, under 10k limit)
- **Reply limit**: Track replies per day, cap at ~50/day to stay under 1,500/month
- **Duplicate check**: Store replied tweet IDs to avoid double-replying
- **Error handling**: Log failures, don't crash the loop

## MVP Scope

### In Scope
- Poll mentions every 5 min
- Analyze first image in tweet
- Reply with roast
- Basic rate limiting
- State persistence

### Out of Scope (Future)
- Multiple images per tweet
- Direct messages
- Proactive scanning (quote tweets, hashtags)
- User blocklist
- Analytics/logging dashboard

## Deployment

1. Add Twitter secrets to AWS Secrets Manager
2. Update `app/config.py` to load Twitter secrets
3. Implement the components above
4. SSH to EC2, attach to tmux
5. Open new pane: `Ctrl+B, C`
6. Run: `python -m app.twitter.bot`
7. Detach: `Ctrl+B, D`

## Dependencies

Add to `pyproject.toml`:

```toml
tweepy = "^4.14"  # or use httpx directly
```

## Estimated Effort

| Task | Time |
|------|------|
| Twitter developer setup + keys | 30 min |
| Twitter client wrapper | 1 hr |
| Celery task for Twitter | 30 min |
| Roast prompt tuning | 30 min |
| Polling loop | 1 hr |
| Testing & debugging | 1-2 hr |
| **Total** | **4-6 hours** |
