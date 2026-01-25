
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_reader_user
from app.db.database import get_db
from app.models import Category, Edition, Item, ItemCategory
from app.schemas import ItemSubtype, ItemType, ItemWithCategoriesResponse, StoryGroupResponse
from app.services.story_grouping import build_story_groups

router = APIRouter()


@router.get("/edition/{edition_id}/items", response_model=list[ItemWithCategoriesResponse])
async def get_edition_items(
    edition_id: int,
    item_type: ItemType | None = Query(None, description="Filter by item type"),
    subtype: ItemSubtype | None = Query(None, description="Filter by subtype"),
    page_number: int | None = Query(None, description="Filter by page number"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of items to return"),
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
):
    """
    Get items for a specific edition with optional filtering.
    """
    # Verify edition exists
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")

    # Build query
    query = db.query(Item).filter(Item.edition_id == edition_id)

    if item_type:
        query = query.filter(Item.item_type == item_type)

    if subtype:
        query = query.filter(Item.subtype == subtype)

    if page_number:
        query = query.filter(Item.page_number == page_number)

    items = query.offset(skip).limit(limit).all()

    # Load categories for each item
    result = []
    for item in items:
        categories = (
            db.query(ItemCategory, Category)
            .join(Category)
            .filter(ItemCategory.item_id == item.id)
            .all()
        )

        item_categories = []
        for item_cat, cat in categories:
            from app.schemas import CategoryResponse
            item_categories.append({
                "id": item_cat.id,
                "item_id": item_cat.item_id,
                "category_id": item_cat.category_id,
                "confidence": item_cat.confidence,
                "source": item_cat.source,
                "notes": item_cat.notes,
                "created_at": item_cat.created_at,
                "updated_at": item_cat.updated_at,
                "category": CategoryResponse.model_validate(cat)
            })

        result.append({
            **item.__dict__,
            "categories": item_categories
        })

    return result


@router.get("/edition/{edition_id}/story-groups", response_model=list[StoryGroupResponse])
async def get_story_groups(
    edition_id: int,
    skip: int = Query(0, ge=0, description="Number of groups to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of groups to return"),
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
):
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")

    items = (
        db.query(Item)
        .filter(Item.edition_id == edition_id, Item.item_type == ItemType.STORY)
        .order_by(Item.page_number, Item.id)
        .all()
    )
    groups = build_story_groups(items)
    sliced = groups[skip: skip + limit]
    return [
        StoryGroupResponse(
            group_id=group.group_id,
            edition_id=group.edition_id,
            title=group.title,
            pages=group.pages,
            item_ids=group.item_ids,
            items_count=len(group.item_ids),
            excerpt=group.excerpt,
            full_text=None,
        )
        for group in sliced
    ]


@router.get("/edition/{edition_id}/story-groups/{group_id}", response_model=StoryGroupResponse)
async def get_story_group(
    edition_id: int,
    group_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
):
    items = (
        db.query(Item)
        .filter(Item.edition_id == edition_id, Item.item_type == ItemType.STORY)
        .order_by(Item.page_number, Item.id)
        .all()
    )
    groups = build_story_groups(items)
    for group in groups:
        if group.group_id == group_id:
            return StoryGroupResponse(
                group_id=group.group_id,
                edition_id=group.edition_id,
                title=group.title,
                pages=group.pages,
                item_ids=group.item_ids,
                items_count=len(group.item_ids),
                excerpt=group.excerpt,
                full_text=group.full_text,
            )

    raise HTTPException(status_code=404, detail="Story group not found")


@router.get("/item/{item_id}", response_model=ItemWithCategoriesResponse)
async def get_item(
    item_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
):
    """
    Get a specific item by ID.
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Load categories for the item
    categories = (
        db.query(ItemCategory, Category)
        .join(Category)
        .filter(ItemCategory.item_id == item.id)
        .all()
    )

    item_categories = []
    for item_cat, cat in categories:
        from app.schemas import CategoryResponse
        item_categories.append({
            "id": item_cat.id,
            "item_id": item_cat.item_id,
            "category_id": item_cat.category_id,
            "confidence": item_cat.confidence,
            "source": item_cat.source,
            "notes": item_cat.notes,
            "created_at": item_cat.created_at,
            "updated_at": item_cat.updated_at,
            "category": CategoryResponse.model_validate(cat)
        })

    return {
        **item.__dict__,
        "categories": item_categories
    }
