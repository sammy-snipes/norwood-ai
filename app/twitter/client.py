"""Twitter API client wrapper."""

import logging
from dataclasses import dataclass

import tweepy

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Tweet:
    """Simplified tweet data."""

    id: str
    text: str
    author_id: str
    author_username: str
    media_urls: list[str]


def get_client() -> tweepy.Client:
    """Get authenticated Twitter API v2 client."""
    settings = get_settings()
    return tweepy.Client(
        bearer_token=settings.TWITTER_BEARER_TOKEN,
        consumer_key=settings.TWITTER_API_KEY,
        consumer_secret=settings.TWITTER_API_SECRET,
        access_token=settings.TWITTER_ACCESS_TOKEN,
        access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True,
    )


def get_mentions(since_id: str | None = None) -> list[Tweet]:
    """
    Fetch recent mentions of the authenticated user.

    Args:
        since_id: Only return tweets newer than this ID

    Returns:
        List of Tweet objects with media URLs populated
    """
    client = get_client()

    # Get authenticated user's ID
    me = client.get_me()
    if not me.data:
        raise RuntimeError("Failed to get authenticated user")

    user_id = me.data.id

    # Fetch mentions with media expansions
    kwargs = {
        "id": user_id,
        "expansions": ["attachments.media_keys", "author_id"],
        "media_fields": ["url", "preview_image_url", "type"],
        "user_fields": ["username"],
        "tweet_fields": ["author_id"],
        "max_results": 10,
    }
    if since_id:
        kwargs["since_id"] = since_id

    response = client.get_users_mentions(**kwargs)

    if not response.data:
        return []

    # Build media lookup from includes
    media_lookup: dict[str, str] = {}
    if response.includes and "media" in response.includes:
        for media in response.includes["media"]:
            if media.type == "photo" and media.url:
                media_lookup[media.media_key] = media.url

    # Build user lookup
    user_lookup: dict[str, str] = {}
    if response.includes and "users" in response.includes:
        for user in response.includes["users"]:
            user_lookup[user.id] = user.username

    tweets = []
    for tweet in response.data:
        media_urls = []
        if tweet.attachments and "media_keys" in tweet.attachments:
            for key in tweet.attachments["media_keys"]:
                if key in media_lookup:
                    media_urls.append(media_lookup[key])

        tweets.append(
            Tweet(
                id=str(tweet.id),
                text=tweet.text,
                author_id=str(tweet.author_id),
                author_username=user_lookup.get(tweet.author_id, "unknown"),
                media_urls=media_urls,
            )
        )

    return tweets


def reply_to_tweet(tweet_id: str, text: str) -> str | None:
    """
    Post a reply to a tweet.

    Args:
        tweet_id: ID of the tweet to reply to
        text: Reply text (max 280 chars)

    Returns:
        ID of the reply tweet, or None on failure
    """
    client = get_client()

    if len(text) > 280:
        text = text[:277] + "..."

    try:
        response = client.create_tweet(
            text=text,
            in_reply_to_tweet_id=tweet_id,
        )
        if response.data:
            logger.info(f"Posted reply to {tweet_id}: {response.data['id']}")
            return str(response.data["id"])
        return None
    except tweepy.TweepyException as e:
        logger.error(f"Failed to reply to {tweet_id}: {e}")
        return None
