"""
Reddit Community Insights Routes
Exposes Reddit posts for travel destinations.
"""

from fastapi import APIRouter, HTTPException, Query
from app.services.reddit_service import RedditService, RedditInsightsResponse

router = APIRouter(prefix="/api/v1/reddit", tags=["reddit"])
reddit_service = RedditService()


@router.get("/city/{city_name}", response_model=RedditInsightsResponse)
async def city_reddit_insights(
    city_name: str,
    limit_per_sub: int = Query(4, ge=1, le=10, description="Posts to fetch per subreddit"),
):
    """
    Fetch top Reddit posts about a city from r/travel, r/solotravel,
    r/backpacking, r/digitalnomad, r/shoestring, and the city's own
    subreddit (if one exists).
    """
    if not city_name.strip():
        raise HTTPException(status_code=400, detail="city_name is required")
    try:
        result = await reddit_service.get_city_insights(
            city_name.strip(),
            limit_per_sub=limit_per_sub,
        )
        return result
    except Exception as e:
        # Gracefully degrade — Reddit is best-effort
        return RedditInsightsResponse(city=city_name, posts=[], community_subreddit=None)
