

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.auth import get_reader_user
from app.db.database import get_db
from app.models import Edition, Item
from app.schemas import GlobalSearchResult, ItemSubtype, ItemType, SearchResult

router = APIRouter()


@router.get("/edition/{edition_id}/search", response_model=list[SearchResult])
async def search_edition(
    edition_id: int,
    q: str = Query(..., min_length=2, description="Search query"),
    item_type: ItemType | None = Query(None, description="Filter by item type"),
    subtype: ItemSubtype | None = Query(None, description="Filter by subtype"),
    page_number: int | None = Query(None, description="Filter by page number"),
    has_phone: bool | None = Query(None, description="Filter classifieds with phone numbers"),
    has_email: bool | None = Query(None, description="Filter classifieds with email addresses"),
    has_price: bool | None = Query(None, description="Filter classifieds with price information"),
    property_type: str | None = Query(None, description="Filter property classifieds by type"),
    min_bedrooms: int | None = Query(None, description="Filter property by minimum bedrooms"),
    max_bedrooms: int | None = Query(None, description="Filter property by maximum bedrooms"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
):
    """
    Search within an edition for items matching the query.

    Searches through item titles and text content.
    """
    # Verify edition exists
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")

    # Build search query
    query = db.query(Item).filter(Item.edition_id == edition_id)

    # Add text search condition
    search_condition = or_(
        Item.title.ilike(f"%{q}%"),
        Item.text.ilike(f"%{q}%")
    )
    query = query.filter(search_condition)

    # Add filters
    if item_type:
        query = query.filter(Item.item_type == item_type)

    if subtype:
        query = query.filter(Item.subtype == subtype)

    if page_number:
        query = query.filter(Item.page_number == page_number)

    # Execute query with pagination (structured filters applied client-side)
    items = query.offset(skip).limit(limit).all()

    # Apply structured classifieds filters client-side
    if has_phone or has_email or has_price or property_type or min_bedrooms or max_bedrooms:
        filtered_items = []
        for item in items:
            if str(item.item_type) != ItemType.CLASSIFIED:
                continue

            contact_info = item.contact_info_json or {}
            price_info = item.price_info_json or {}
            details = item.classification_details_json or {}

            # Apply filters
            if has_phone and not contact_info.get('phone_numbers'):
                continue
            if has_email and not contact_info.get('email_addresses'):
                continue
            if has_price and not price_info:
                continue
            if property_type and str(item.subtype) == ItemSubtype.PROPERTY:
                if details.get('property_type') != property_type:
                    continue
            if min_bedrooms and str(item.subtype) == ItemSubtype.PROPERTY:
                bedrooms = details.get('bedrooms')
                if not bedrooms or int(bedrooms) < min_bedrooms:
                    continue
            if max_bedrooms and str(item.subtype) == ItemSubtype.PROPERTY:
                bedrooms = details.get('bedrooms')
                if not bedrooms or int(bedrooms) > max_bedrooms:
                    continue

            filtered_items.append(item)

        items = filtered_items

    # Convert to search results
    results = []
    for item in items:
        # Create snippet highlighting the search term
        snippet = ""
        highlights = []

        if item.text and q.lower() in item.text.lower():
            # Find the first occurrence and create snippet
            text_lower = item.text.lower()
            q_lower = q.lower()
            pos = text_lower.find(q_lower)

            if pos != -1:
                start = max(0, pos - 100)
                end = min(len(item.text), pos + len(q) + 100)
                snippet = item.text[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(item.text):
                    snippet = snippet + "..."
                highlights.append(q)

        elif item.title and q.lower() in item.title.lower():
            snippet = item.title
            highlights.append(q)
        else:
            snippet = (item.title or "")[:200] + ("..." if item.title and len(item.title) > 200 else "")

        results.append(SearchResult(
            item_id=item.id,
            title=item.title,
            page_number=item.page_number,
            snippet=snippet,
            highlights=highlights
        ))

    return results


@router.get("/search", response_model=list[GlobalSearchResult])
async def search_all_editions(
    q: str = Query(..., min_length=2, description="Search query"),
    item_type: ItemType | None = Query(None, description="Filter by item type"),
    subtype: ItemSubtype | None = Query(None, description="Filter by subtype"),
    newspaper_name: str | None = Query(None, description="Filter by newspaper name"),
    date_from: str | None = Query(None, description="Filter editions from this date (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="Filter editions to this date (YYYY-MM-DD)"),
    has_phone: bool | None = Query(None, description="Filter classifieds with phone numbers"),
    has_email: bool | None = Query(None, description="Filter classifieds with email addresses"),
    has_price: bool | None = Query(None, description="Filter classifieds with price information"),
    property_type: str | None = Query(None, description="Filter property classifieds by type"),
    min_bedrooms: int | None = Query(None, description="Filter property by minimum bedrooms"),
    max_bedrooms: int | None = Query(None, description="Filter property by maximum bedrooms"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
):
    """
    Search across all editions for items matching the query.

    Searches through item titles and text content across all editions.
    """
    from datetime import datetime

    # Build search query with edition join
    query = db.query(Item).join(Edition)

    # Add text search condition
    search_condition = or_(
        Item.title.ilike(f"%{q}%"),
        Item.text.ilike(f"%{q}%")
    )
    query = query.filter(search_condition)

    # Add filters
    if item_type:
        query = query.filter(Item.item_type == item_type)

    if subtype:
        query = query.filter(Item.subtype == subtype)

    if newspaper_name:
        query = query.filter(Edition.newspaper_name.ilike(f"%{newspaper_name}%"))

    # Add date filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Edition.edition_date >= date_from_obj)
        except ValueError as err:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD") from err

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Edition.edition_date <= date_to_obj)
        except ValueError as err:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD") from err

    # Execute query with pagination
    items = query.offset(skip).limit(limit).all()

    # Convert to global search results
    results = []
    for item in items:
        # Create snippet highlighting the search term
        snippet = ""
        highlights = []

        if item.text and q.lower() in item.text.lower():
            # Find the first occurrence and create snippet
            text_lower = item.text.lower()
            q_lower = q.lower()
            pos = text_lower.find(q_lower)

            if pos != -1:
                start = max(0, pos - 100)
                end = min(len(item.text), pos + len(q) + 100)
                snippet = item.text[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(item.text):
                    snippet = snippet + "..."
                highlights.append(q)

        elif item.title and q.lower() in item.title.lower():
            snippet = item.title
            highlights.append(q)
        else:
            snippet = (item.title or "")[:200] + ("..." if item.title and len(item.title) > 200 else "")

        results.append(GlobalSearchResult(
            item_id=item.id,
            title=item.title,
            page_number=item.page_number,
            snippet=snippet,
            highlights=highlights,
            edition_id=item.edition_id,
            newspaper_name=item.edition.newspaper_name,
            edition_date=item.edition.edition_date,
            item_type=item.item_type,
            subtype=item.subtype
        ))

    return results
