
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models import Favorite, Item, User
from app.schemas import FavoriteCreate, FavoriteResponse

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("/", response_model=list[FavoriteResponse])
async def list_favorites(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    include_items: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all favorites for the current user."""
    query = db.query(Favorite).filter(Favorite.user_id == current_user.id)
    favorites = query.offset(skip).limit(limit).all()

    if include_items:
        # Items are loaded as needed via relationship
        pass

    return favorites


@router.post("/", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
async def create_favorite(
    favorite_in: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an item to favorites."""
    # Check if item exists
    item = db.query(Item).filter(Item.id == favorite_in.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Check if already favorited
    existing = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.item_id == favorite_in.item_id
    ).first()

    if existing:
        return existing

    db_favorite = Favorite(
        user_id=current_user.id,
        item_id=favorite_in.item_id,
        notes=favorite_in.notes
    )
    db.add(db_favorite)
    db.commit()
    db.refresh(db_favorite)
    return db_favorite


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a favorite by its ID."""
    favorite = db.query(Favorite).filter(
        Favorite.id == favorite_id,
        Favorite.user_id == current_user.id
    ).first()

    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(favorite)
    db.commit()


@router.delete("/item/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite_by_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a favorite by item ID."""
    favorite = db.query(Favorite).filter(
        Favorite.item_id == item_id,
        Favorite.user_id == current_user.id
    ).first()

    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(favorite)
    db.commit()
