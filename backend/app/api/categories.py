"""
API endpoints for category management and item classification.
"""

import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.api.auth import get_admin_user
from app.db.database import get_db
from app.models import Category, ItemCategory, Item, User
from app.schemas import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryWithStats,
    ItemCategoryCreate, ItemCategoryResponse, ItemWithCategories,
    BatchClassificationRequest, BatchClassificationResponse,
    ClassificationStats
)
from app.services.category_classifier import CategoryClassifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["categories"])


# Category Management Endpoints
@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """List all categories."""
    query = db.query(Category)
    
    if active_only:
        query = query.filter(Category.is_active == True)
    
    categories = query.order_by(Category.sort_order, Category.name).offset(skip).limit(limit).all()
    return categories


@router.get("/{category_id}", response_model=CategoryWithStats)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get category details with statistics."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get item count
    item_count = db.query(func.count(ItemCategory.category_id)).filter(
        ItemCategory.category_id == category_id
    ).scalar() or 0
    
    # Get average confidence
    avg_confidence = db.query(func.avg(ItemCategory.confidence)).filter(
        ItemCategory.category_id == category_id
    ).scalar()
    
    # Get recent items (last 30 days)
    recent_date = datetime.utcnow() - timedelta(days=30)
    recent_items = db.query(func.count(ItemCategory.id)).filter(
        ItemCategory.category_id == category_id,
        ItemCategory.created_at >= recent_date
    ).scalar() or 0
    
    return CategoryWithStats(
        **category.__dict__,
        item_count=item_count,
        avg_confidence=float(avg_confidence) if avg_confidence else None,
        recent_items=recent_items
    )


@router.get("/slug/{slug}", response_model=CategoryWithStats)
async def get_category_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get category by slug with statistics."""
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Redirect to get_category with ID
    return await get_category(category.id, db)


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Create a new category (admin only)."""
    # Check if slug already exists
    existing = db.query(Category).filter(Category.slug == category.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this slug already exists")
    
    db_category = Category(**category.model_dump())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    
    logger.info(f"Created category '{category.name}' by admin user {admin_user.email}")
    return db_category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Update a category (admin only)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Update fields
    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    
    logger.info(f"Updated category '{category.name}' by admin user {admin_user.email}")
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Delete a category (admin only)."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(category)
    db.commit()
    
    logger.info(f"Deleted category '{category.name}' by admin user {admin_user.email}")


# Items in Category Endpoints
@router.get("/{category_id}/items", response_model=List[ItemWithCategories])
async def get_items_in_category(
    category_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    min_confidence: int = Query(0, ge=0, le=100),
    db: Session = Depends(get_db)
):
    """Get items in a specific category."""
    # Verify category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Get items with categories
    items = (
        db.query(Item)
        .join(ItemCategory)
        .filter(
            ItemCategory.category_id == category_id,
            ItemCategory.confidence >= min_confidence
        )
        .order_by(desc(ItemCategory.confidence), Item.page_number)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
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
            item_categories.append(
                ItemCategoryResponse(
                    **item_cat.__dict__,
                    category=CategoryResponse(**cat.__dict__)
                )
            )
        
        result.append(
            ItemWithCategories(
                **item.__dict__,
                categories=item_categories
            )
        )
    
    return result


# Item Classification Endpoints
@router.post("/items/{item_id}/categories", response_model=ItemCategoryResponse)
async def add_item_category(
    item_id: int,
    classification: ItemCategoryCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Manually assign a category to an item (admin only)."""
    # Verify item exists
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Verify category exists
    category = db.query(Category).filter(Category.id == classification.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if classification already exists
    existing = db.query(ItemCategory).filter(
        ItemCategory.item_id == item_id,
        ItemCategory.category_id == classification.category_id
    ).first()
    
    if existing:
        # Update existing classification
        existing.confidence = classification.confidence
        existing.source = "manual"
        existing.notes = classification.notes
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        item_category = existing
    else:
        # Create new classification
        item_category = ItemCategory(
            item_id=item_id,
            category_id=classification.category_id,
            confidence=classification.confidence,
            source="manual",
            notes=classification.notes
        )
        db.add(item_category)
        db.commit()
        db.refresh(item_category)
    
    logger.info(f"Added manual category '{category.name}' to item {item_id} by admin user {admin_user.email}")
    
    return ItemCategoryResponse(
        **item_category.__dict__,
        category=CategoryResponse(**category.__dict__)
    )


@router.delete("/items/{item_id}/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item_category(
    item_id: int,
    category_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Remove a category from an item (admin only)."""
    item_category = db.query(ItemCategory).filter(
        ItemCategory.item_id == item_id,
        ItemCategory.category_id == category_id
    ).first()
    
    if not item_category:
        raise HTTPException(status_code=404, detail="Item classification not found")
    
    category = db.query(Category).filter(Category.id == category_id).first()
    db.delete(item_category)
    db.commit()
    
    logger.info(f"Removed category '{category.name}' from item {item_id} by admin user {admin_user.email}")


# Batch Classification Endpoints
@router.post("/batch-classify", response_model=BatchClassificationResponse)
async def batch_classify_items(
    request: BatchClassificationRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Run batch classification on specified items (admin only)."""
    start_time = datetime.utcnow()
    
    # Verify items exist
    items = db.query(Item).filter(Item.id.in_(request.item_ids)).all()
    if not items:
        raise HTTPException(status_code=404, detail="No items found")
    
    found_item_ids = [item.id for item in items]
    failed_items = set(request.item_ids) - set(found_item_ids)
    
    # Run classification
    try:
        classifier = CategoryClassifier(db)
        results = classifier.batch_classify_items(
            items,
            confidence_threshold=request.confidence_threshold,
            clear_existing=request.clear_existing
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        response = BatchClassificationResponse(
            total_items=len(items),
            items_classified=len(results),
            total_classifications=sum(len(classifications) for classifications in results.values()),
            failed_items=list(failed_items),
            processing_time=processing_time
        )
        
        logger.info(
            f"Batch classification completed by admin user {admin_user.email}: "
            f"{response.items_classified}/{response.total_items} items classified "
            f"in {processing_time:.2f}s"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Batch classification failed: {e}")
        raise HTTPException(status_code=500, detail="Classification failed")


@router.post("/reclassify-all", response_model=ClassificationStats)
async def reclassify_all_items(
    confidence_threshold: int = Query(30, ge=0, le=100),
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """Re-run classification on all items in the database (admin only)."""
    try:
        classifier = CategoryClassifier(db)
        stats = classifier.reclassify_all_items(confidence_threshold)
        
        logger.info(
            f"Full reclassification completed by admin user {admin_user.email}: "
            f"{stats['items_classified']}/{stats['total_items']} items classified"
        )
        
        return ClassificationStats(
            total_items=stats['total_items'],
            items_classified=stats['items_classified'],
            total_classifications=stats['total_classifications'],
            classification_rate=stats['items_classified'] / stats['total_items'] if stats['total_items'] > 0 else 0,
            avg_categories_per_item=stats['total_classifications'] / stats['items_classified'] if stats['items_classified'] > 0 else 0
        )
        
    except Exception as e:
        logger.error(f"Full reclassification failed: {e}")
        raise HTTPException(status_code=500, detail="Reclassification failed")


# Category Suggestions Endpoint
@router.post("/suggest", response_model=List[CategoryResponse])
async def get_category_suggestions(
    text: str,
    limit: int = Query(5, ge=1, le=10),
    confidence_threshold: int = Query(30, ge=0, le=100),
    db: Session = Depends(get_db)
):
    """Get category suggestions for arbitrary text."""
    if not text or len(text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Text too short for classification")
    
    try:
        classifier = CategoryClassifier(db)
        suggestions = classifier.get_category_suggestions(text, limit)
        
        # Filter by confidence threshold and return categories
        result = []
        for category, confidence in suggestions:
            if confidence >= confidence_threshold:
                result.append(CategoryResponse(**category.__dict__))
        
        return result
        
    except Exception as e:
        logger.error(f"Category suggestions failed: {e}")
        raise HTTPException(status_code=500, detail="Classification failed")