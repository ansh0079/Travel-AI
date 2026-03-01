"""
Reddit Community Insights Service
Fetches travel-related Reddit posts for destinations using Reddit's public JSON API.
No authentication required for public subreddits.
"""

import httpx
import asyncio
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

REDDIT_USER_AGENT = "TravelAI/1.0 (travel destination research tool)"
REDDIT_BASE = "https://www.reddit.com"

# Primary travel subreddits to search for destination content
TRAVEL_SUBREDDITS = ["travel", "solotravel", "backpacking", "digitalnomad", "shoestring"]


class RedditPost(BaseModel):
    id: str
    title: str
    subreddit: str
    score: int
    num_comments: int
    url: str
    permalink: str
    flair: Optional[str] = None
    thumbnail: Optional[str] = None
    created_utc: float
    preview_text: Optional[str] = None


class RedditInsightsResponse(BaseModel):
    city: str
    posts: List[RedditPost]
    community_subreddit: Optional[str] = None  # e.g. r/paris if it exists


class RedditService:
    """Fetches Reddit posts for travel destinations using public JSON API."""

    async def _fetch_subreddit_search(
        self,
        client: httpx.AsyncClient,
        subreddit: str,
        query: str,
        limit: int = 5,
    ) -> List[RedditPost]:
        """Search a single subreddit for posts matching the city query."""
        try:
            url = f"{REDDIT_BASE}/r/{subreddit}/search.json"
            response = await client.get(
                url,
                params={
                    "q": query,
                    "sort": "top",
                    "t": "year",
                    "limit": limit,
                    "restrict_sr": "1",
                },
                timeout=8.0,
                headers={"User-Agent": REDDIT_USER_AGENT},
            )
            if response.status_code != 200:
                return []

            data = response.json()
            posts = []
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                if not post:
                    continue

                # Skip stickied/mod posts and low-quality posts
                if post.get("stickied") or post.get("score", 0) < 5:
                    continue

                # Get thumbnail if it's a real image URL
                thumb = post.get("thumbnail", "")
                if thumb in ("self", "default", "nsfw", "spoiler", ""):
                    thumb = None

                # Get selftext preview (first 200 chars)
                selftext = post.get("selftext", "") or ""
                preview = selftext[:200].strip() if selftext else None

                posts.append(
                    RedditPost(
                        id=post["id"],
                        title=post["title"],
                        subreddit=post["subreddit"],
                        score=post.get("score", 0),
                        num_comments=post.get("num_comments", 0),
                        url=post.get("url", ""),
                        permalink=f"https://reddit.com{post.get('permalink', '')}",
                        flair=post.get("link_flair_text"),
                        thumbnail=thumb,
                        created_utc=post.get("created_utc", 0),
                        preview_text=preview if preview else None,
                    )
                )
            return posts
        except Exception as e:
            logger.warning(f"Reddit search failed for r/{subreddit}", error=str(e))
            return []

    async def _fetch_city_subreddit(
        self,
        client: httpx.AsyncClient,
        city_name: str,
        limit: int = 3,
    ) -> tuple[Optional[str], List[RedditPost]]:
        """Try to fetch posts from a city-specific subreddit (e.g. r/paris)."""
        slug = city_name.lower().replace(" ", "")
        try:
            url = f"{REDDIT_BASE}/r/{slug}/hot.json"
            response = await client.get(
                url,
                params={"limit": limit},
                timeout=6.0,
                headers={"User-Agent": REDDIT_USER_AGENT},
            )
            if response.status_code != 200:
                return None, []

            data = response.json()
            # Confirm it's a real subreddit (not a redirect)
            sub_data = data.get("data", {})
            children = sub_data.get("children", [])
            if not children:
                return None, []

            posts = []
            for child in children:
                post = child.get("data", {})
                if not post or post.get("stickied"):
                    continue

                thumb = post.get("thumbnail", "")
                if thumb in ("self", "default", "nsfw", "spoiler", ""):
                    thumb = None

                selftext = post.get("selftext", "") or ""
                preview = selftext[:200].strip() if selftext else None

                posts.append(
                    RedditPost(
                        id=post["id"],
                        title=post["title"],
                        subreddit=post["subreddit"],
                        score=post.get("score", 0),
                        num_comments=post.get("num_comments", 0),
                        url=post.get("url", ""),
                        permalink=f"https://reddit.com{post.get('permalink', '')}",
                        flair=post.get("link_flair_text"),
                        thumbnail=thumb,
                        created_utc=post.get("created_utc", 0),
                        preview_text=preview if preview else None,
                    )
                )
            return f"r/{slug}" if posts else None, posts
        except Exception as e:
            logger.debug(f"No city subreddit for {slug}", error=str(e))
            return None, []

    async def get_city_insights(
        self,
        city_name: str,
        limit_per_sub: int = 4,
    ) -> RedditInsightsResponse:
        """
        Fetch top Reddit posts about a city from multiple travel subreddits
        plus the city's own subreddit (if it exists).
        Returns deduplicated posts sorted by score.
        """
        async with httpx.AsyncClient() as client:
            # Search travel subreddits + try city subreddit in parallel
            tasks = [
                self._fetch_subreddit_search(client, sub, city_name, limit=limit_per_sub)
                for sub in TRAVEL_SUBREDDITS
            ]
            tasks.append(self._fetch_city_subreddit(client, city_name))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate city subreddit result (last task) from search results
        city_sub_result = results[-1]
        search_results = results[:-1]

        community_subreddit: Optional[str] = None
        city_posts: List[RedditPost] = []

        if isinstance(city_sub_result, tuple):
            community_subreddit, city_posts = city_sub_result

        # Combine all posts, deduplicate by post id
        all_posts: List[RedditPost] = []
        seen_ids: set[str] = set()

        # City subreddit posts first
        for post in city_posts:
            if post.id not in seen_ids:
                seen_ids.add(post.id)
                all_posts.append(post)

        # Travel subreddit search results
        for result in search_results:
            if isinstance(result, list):
                for post in result:
                    if post.id not in seen_ids:
                        seen_ids.add(post.id)
                        all_posts.append(post)

        # Sort by score descending, cap at 15 total
        all_posts.sort(key=lambda p: p.score, reverse=True)
        all_posts = all_posts[:15]

        logger.info(
            f"Reddit insights for {city_name}",
            post_count=len(all_posts),
            community_sub=community_subreddit,
        )

        return RedditInsightsResponse(
            city=city_name,
            posts=all_posts,
            community_subreddit=community_subreddit,
        )
