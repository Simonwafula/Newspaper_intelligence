from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.auth import get_admin_user, get_reader_user
from app.db.database import get_db
from app.schemas import SavedSearchCreate, SavedSearchResponse
from app.services.saved_search_service import SavedSearchService

router = APIRouter()


@router.post("/saved-searches", response_model=SavedSearchResponse)
def create_saved_search(
    search: SavedSearchCreate,
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
) -> Any:
    """Create a new saved search."""
    service = SavedSearchService(db)

    # Check if search with same name already exists
    existing = service.get_by_name(search.name)
    if existing:
        raise HTTPException(status_code=400, detail="Saved search with this name already exists")

    return service.create(search)


@router.get("/saved-searches", response_model=list[SavedSearchResponse])
def list_saved_searches(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
) -> Any:
    """List saved searches."""
    service = SavedSearchService(db)
    return service.list(skip=skip, limit=limit, active_only=active_only)


@router.get("/saved-searches/{search_id}", response_model=SavedSearchResponse)
def get_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
) -> Any:
    """Get a specific saved search."""
    service = SavedSearchService(db)
    search = service.get(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return search


@router.put("/saved-searches/{search_id}", response_model=SavedSearchResponse)
def update_saved_search(
    search_id: int,
    search_update: SavedSearchCreate,
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
) -> Any:
    """Update a saved search."""
    service = SavedSearchService(db)
    search = service.update(search_id, search_update)
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return search


@router.delete("/saved-searches/{search_id}")
def delete_saved_search(
    search_id: int,
    db: Session = Depends(get_db),
    _user = Depends(get_reader_user)
) -> Any:
    """Delete a saved search."""
    service = SavedSearchService(db)
    success = service.delete(search_id)
    if not success:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"message": "Saved search deleted successfully"}


@router.post("/saved-searches/{search_id}/update-matches", response_model=SavedSearchResponse)
def update_search_matches(
    search_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(get_admin_user)
) -> Any:
    """Update the match count for a saved search."""
    service = SavedSearchService(db)
    search = service.update_match_count(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return search


@router.post("/saved-searches/update-all-matches")
def update_all_search_matches(
    db: Session = Depends(get_db),
    _: None = Depends(get_admin_user)
) -> Any:
    """Update match counts for all active saved searches."""
    service = SavedSearchService(db)
    results = service.update_all_match_counts()
    return {
        "message": f"Updated {results['updated']} searches",
        "updated": results['updated'],
        "failed": results['failed']
    }
