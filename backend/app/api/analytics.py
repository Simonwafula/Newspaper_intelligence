from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models import Category, Edition, Item, ItemCategory, User
from app.schemas import TopicTrend, TrendDashboardResponse, VolumeTrend

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/trends", response_model=TrendDashboardResponse)
async def get_trends(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get topic and volume trends for the dashboard."""
    start_date = datetime.now(UTC) - timedelta(days=days)

    # 1. Volume trends (items per day)
    volume_data = (
        db.query(
            func.date(Edition.edition_date).label("date"),
            func.count(Item.id).label("count")
        )
        .join(Item, Edition.id == Item.edition_id)
        .filter(Edition.edition_date >= start_date)
        .group_by(func.date(Edition.edition_date))
        .order_by("date")
        .all()
    )

    volume_trends = [
        VolumeTrend(date=datetime.strptime(str(d.date), "%Y-%m-%d"), count=d.count)
        for d in volume_data
    ]

    # 2. Topic trends (top categories over time)
    # For now, just get top 5 categories
    top_categories_data = (
        db.query(
            Category.name,
            func.count(ItemCategory.id).label("count")
        )
        .join(ItemCategory, Category.id == ItemCategory.category_id)
        .group_by(Category.name)
        .order_by(desc("count"))
        .limit(5)
        .all()
    )

    top_categories = [{"name": c.name, "count": c.count} for c in top_categories_data]
    category_names = [c["name"] for c in top_categories]

    topic_trends_data = (
        db.query(
            Category.name.label("category_name"),
            func.date(Edition.edition_date).label("date"),
            func.count(ItemCategory.id).label("count")
        )
        .join(ItemCategory, Category.id == ItemCategory.category_id)
        .join(Item, ItemCategory.item_id == Item.id)
        .join(Edition, Item.edition_id == Edition.id)
        .filter(Edition.edition_date >= start_date)
        .filter(Category.name.in_(category_names))
        .group_by("category_name", func.date(Edition.edition_date))
        .order_by("date")
        .all()
    )

    topic_trends = [
        TopicTrend(
            category_name=t.category_name,
            date=datetime.strptime(str(t.date), "%Y-%m-%d"),
            count=t.count
        )
        for t in topic_trends_data
    ]

    return TrendDashboardResponse(
        topic_trends=topic_trends,
        volume_trends=volume_trends,
        top_categories=top_categories
    )
