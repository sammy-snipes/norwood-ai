"""Twitter bot polling loop."""

import base64
import json
import logging
import sys
import time
from pathlib import Path

import httpx

from app.tasks.twitter import analyze_twitter_image_task
from app.twitter.client import Tweet, get_mentions, reply_to_tweet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

STATE_FILE = Path("/tmp/norwood_twitter_state.json")
POLL_INTERVAL_SECONDS = 300  # 5 minutes
TASK_TIMEOUT_SECONDS = 120  # 2 minutes to wait for Celery task


def load_state() -> dict:
    """Load bot state from file."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load state: {e}")
    return {"last_seen_id": None, "replied_tweets": []}


def save_state(state: dict) -> None:
    """Save bot state to file."""
    # Keep only last 1000 replied tweet IDs to prevent unbounded growth
    if len(state.get("replied_tweets", [])) > 1000:
        state["replied_tweets"] = state["replied_tweets"][-1000:]
    STATE_FILE.write_text(json.dumps(state, indent=2))


def download_image(url: str) -> tuple[str, str] | None:
    """
    Download image from URL and return as base64.

    Returns:
        Tuple of (base64_data, media_type) or None on failure
    """
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "image/jpeg")
            if ";" in content_type:
                content_type = content_type.split(";")[0].strip()

            b64_data = base64.standard_b64encode(response.content).decode("utf-8")
            return (b64_data, content_type)
    except Exception as e:
        logger.error(f"Failed to download image {url}: {e}")
        return None


def process_tweet(tweet: Tweet, state: dict) -> bool:
    """
    Process a single tweet with image.

    Returns:
        True if successfully processed and replied
    """
    if tweet.id in state.get("replied_tweets", []):
        logger.info(f"Already replied to {tweet.id}, skipping")
        return False

    if not tweet.media_urls:
        logger.info(f"Tweet {tweet.id} has no images, skipping")
        return False

    # Download first image
    image_url = tweet.media_urls[0]
    logger.info(f"Downloading image from {image_url}")
    image_data = download_image(image_url)

    if not image_data:
        logger.error(f"Failed to download image for tweet {tweet.id}")
        return False

    image_base64, media_type = image_data

    # Queue analysis task
    logger.info(f"Queuing analysis for tweet {tweet.id}")
    task = analyze_twitter_image_task.delay(image_base64, media_type)

    # Wait for result
    try:
        result = task.get(timeout=TASK_TIMEOUT_SECONDS)
    except Exception as e:
        logger.error(f"Task failed or timed out for tweet {tweet.id}: {e}")
        return False

    if not result.get("success"):
        logger.error(f"Analysis failed for tweet {tweet.id}: {result.get('error')}")
        return False

    reply_text = result["reply_text"]
    logger.info(f"Replying to @{tweet.author_username}: {reply_text}")

    # Post reply
    reply_id = reply_to_tweet(tweet.id, reply_text)
    if reply_id:
        state.setdefault("replied_tweets", []).append(tweet.id)
        save_state(state)
        logger.info(f"Successfully replied to tweet {tweet.id}")
        return True

    return False


def run_poll_cycle(state: dict) -> dict:
    """Run a single polling cycle."""
    logger.info("Polling for mentions...")

    try:
        mentions = get_mentions(since_id=state.get("last_seen_id"))
    except Exception as e:
        logger.error(f"Failed to fetch mentions: {e}")
        return state

    if not mentions:
        logger.info("No new mentions")
        return state

    logger.info(f"Found {len(mentions)} new mentions")

    for tweet in mentions:
        logger.info(f"Processing tweet {tweet.id} from @{tweet.author_username}")

        if tweet.media_urls:
            process_tweet(tweet, state)
        else:
            logger.info(f"Tweet {tweet.id} has no images, skipping")

        # Update last_seen_id to highest processed
        if state.get("last_seen_id") is None or int(tweet.id) > int(state["last_seen_id"]):
            state["last_seen_id"] = tweet.id
            save_state(state)

    return state


def main():
    """Main bot loop."""
    logger.info("Starting Norwood Twitter bot")
    logger.info(f"Poll interval: {POLL_INTERVAL_SECONDS}s")
    logger.info(f"State file: {STATE_FILE}")

    state = load_state()
    logger.info(f"Loaded state: last_seen_id={state.get('last_seen_id')}")

    while True:
        try:
            state = run_poll_cycle(state)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            save_state(state)
            sys.exit(0)
        except Exception as e:
            logger.error(f"Error in poll cycle: {e}", exc_info=True)

        logger.info(f"Sleeping for {POLL_INTERVAL_SECONDS}s...")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
