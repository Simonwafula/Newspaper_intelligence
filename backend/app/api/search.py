from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.db.database import get_db
from app.models import Item, Edition
from app.schemas import ItemType, ItemSubtype, SearchResult

router = APIRouter()


@router.get("/edition/{edition_id}/search", response_model=List[SearchResult])
async def search_edition(
    edition_id: int,
    q: str = Query(..., min_length=2, description="Search query"),
    item_type: Optional[ItemType] = Query(None, description="Filter by item type"),
    subtype: Optional[ItemSubtype] = Query(None, description="Filter by subtype"),
    page_number: Optional[int] = Query(None, description="Filter by page number"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
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
    
    # Execute query with pagination
    items = query.offset(skip).limit(limit).all()
    
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


@router.get("/search", response_model=List[SearchResult])
async def search_all_editions(
    q: str = Query(..., min_length=2, description="Search query"),
    item_type: Optional[ItemType] = Query(None, description="Filter by item type"),
    subtype: Optional[ItemSubtype] = Query(None, description="Filter by subtype"),
    newspaper_name: Optional[str] = Query(None, description="Filter by newspaper name"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of results to return"),
    db: Session = Depends(get_db)
):
    """
    Search across all editions for items matching the query.
    
    Searches through item titles and text content across all editions.
    """
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
    
    # Execute query with pagination
    items = query.offset(skip).limit(limit).all()
    
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