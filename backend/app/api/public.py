from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Edition, Item
from app.schemas import EditionPublicResponse, ItemPublicResponse, ItemType

router = APIRouter()


@router.get("/editions", response_model=list[EditionPublicResponse])
async def list_public_editions(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List newspaper editions with public information only.
    
    Provides basic edition information (covers-only access) without requiring authentication.
    Includes newspaper name, date, status, and page count but no processing details.
    
    Args:
        skip: Number of editions to skip (pagination)
        limit: Maximum number of editions to return
        db: Database session
        
    Returns:
        List of public edition information
    """
    # Query only public-safe fields
    editions = db.query(Edition).filter(
        # Only show READY editions to public
        Edition.status == "READY"
    ).order_by(
        Edition.edition_date.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        EditionPublicResponse(
            id=edition.id,
            newspaper_name=edition.newspaper_name,
            edition_date=edition.edition_date,
            num_pages=edition.num_pages,
            status=edition.status
        )
        for edition in editions
    ]


@router.get("/editions/{edition_id}", response_model=EditionPublicResponse)
async def get_public_edition(
    edition_id: int,
    db: Session = Depends(get_db)
):
    """
    Get public information about a specific edition.
    
    Provides basic edition information without requiring authentication.
    Only works for editions that are in READY status.
    
    Args:
        edition_id: ID of the edition
        db: Database session
        
    Returns:
        Public edition information
        
    Raises:
        HTTPException: If edition not found or not ready
    """
    edition = db.query(Edition).filter(
        Edition.id == edition_id,
        Edition.status == "READY"  # Only show ready editions
    ).first()
    
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")
    
    return EditionPublicResponse(
        id=edition.id,
        newspaper_name=edition.newspaper_name,
        edition_date=edition.edition_date,
        num_pages=edition.num_pages,
        status=edition.status
    )


@router.get("/editions/{edition_id}/items", response_model=list[ItemPublicResponse])
async def list_public_edition_items(
    edition_id: int,
    item_type: ItemType | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List items in an edition with public information only.
    
    Provides basic item information (title and first 200 characters of text)
    without requiring authentication. Only works for editions that are READY.
    
    Args:
        edition_id: ID of the edition
        item_type: Filter by item type (STORY, AD, CLASSIFIED)
        skip: Number of items to skip (pagination)
        limit: Maximum number of items to return
        db: Database session
        
    Returns:
        List of public item information
        
    Raises:
        HTTPException: If edition not found or not ready
    """
    # Verify edition exists and is ready
    edition = db.query(Edition).filter(
        Edition.id == edition_id,
        Edition.status == "READY"
    ).first()
    
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found or not ready")
    
    # Build query for items
    query = db.query(Item).filter(Item.edition_id == edition_id)
    
    # Add item type filter if specified
    if item_type:
        query = query.filter(Item.item_type == item_type)
    
    # Get items with pagination
    items = query.order_by(
        Item.page_number, Item.id
    ).offset(skip).limit(limit).all()
    
    # Return public-safe information only
    return [
        ItemPublicResponse(
            id=item.id,
            edition_id=item.edition_id,
            page_number=item.page_number,
            item_type=item.item_type,
            subtype=item.subtype,
            title=item.title,
            # Only show first 200 characters of text for public access
            text=(item.text or "")[:200] + ("..." if item.text and len(item.text) > 200 else "")
        )
        for item in items
    ]


@router.get("/items/{item_id}", response_model=ItemPublicResponse)
async def get_public_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Get public information about a specific item.
    
    Provides basic item information (title and first 200 characters of text)
    without requiring authentication. Only works for items in READY editions.
    
    Args:
        item_id: ID of the item
        db: Database session
        
    Returns:
        Public item information
        
    Raises:
        HTTPException: If item not found or edition not ready
    """
    # Join with edition to check status
    item = db.query(Item).join(Edition).filter(
        Item.id == item_id,
        Edition.status == "READY"
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found or not available")
    
    return ItemPublicResponse(
        id=item.id,
        edition_id=item.edition_id,
        page_number=item.page_number,
        item_type=item.item_type,
        subtype=item.subtype,
        title=item.title,
        # Only show first 200 characters of text for public access
        text=(item.text or "")[:200] + ("..." if item.text and len(item.text) > 200 else "")
    )