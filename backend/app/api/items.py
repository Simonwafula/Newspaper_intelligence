from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Item, Edition
from app.schemas import ItemType, ItemSubtype
from app.schemas import ItemResponse

router = APIRouter()


@router.get("/edition/{edition_id}/items", response_model=List[ItemResponse])
async def get_edition_items(
    edition_id: int,
    item_type: Optional[ItemType] = Query(None, description="Filter by item type"),
    subtype: Optional[ItemSubtype] = Query(None, description="Filter by subtype"),
    page_number: Optional[int] = Query(None, description="Filter by page number"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of items to return"),
    db: Session = Depends(get_db)
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
    return items


@router.get("/item/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int, db: Session = Depends(get_db)):
    """
    Get a specific item by ID.
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item