from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Edition, Item
from app.models import SavedSearch as SavedSearchModel
from app.schemas import SavedSearchCreate


class SavedSearchService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, search_create: SavedSearchCreate) -> SavedSearchModel:
        """Create a new saved search."""
        db_search = SavedSearchModel(
            name=search_create.name,
            description=search_create.description,
            query=search_create.query,
            item_types=[t.value for t in search_create.item_types] if search_create.item_types else None,
            date_from=search_create.date_from,
            date_to=search_create.date_to,
        )
        self.db.add(db_search)
        self.db.commit()
        self.db.refresh(db_search)

        # Update match count after creation
        self._update_match_count(db_search)
        self.db.commit()

        return db_search

    def get(self, search_id: int) -> SavedSearchModel | None:
        """Get a saved search by ID."""
        return self.db.query(SavedSearchModel).filter(SavedSearchModel.id == search_id).first()

    def get_by_name(self, name: str) -> SavedSearchModel | None:
        """Get a saved search by name."""
        return self.db.query(SavedSearchModel).filter(SavedSearchModel.name == name).first()

    def list(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> list[SavedSearchModel]:
        """List saved searches."""
        query = self.db.query(SavedSearchModel)

        if active_only:
            query = query.filter(SavedSearchModel.is_active)

        return query.order_by(SavedSearchModel.created_at.desc()).offset(skip).limit(limit).all()

    def update(self, search_id: int, search_update: SavedSearchCreate) -> SavedSearchModel | None:
        """Update a saved search."""
        db_search = self.get(search_id)
        if not db_search:
            return None

        db_search.name = search_update.name
        db_search.description = search_update.description
        db_search.query = search_update.query
        db_search.item_types = [t.value for t in search_update.item_types] if search_update.item_types else None
        db_search.date_from = search_update.date_from
        db_search.date_to = search_update.date_to
        db_search.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(db_search)

        # Update match count after update
        self._update_match_count(db_search)
        self.db.commit()

        return db_search

    def delete(self, search_id: int) -> bool:
        """Delete a saved search."""
        db_search = self.get(search_id)
        if not db_search:
            return False

        self.db.delete(db_search)
        self.db.commit()
        return True

    def update_match_count(self, search_id: int) -> SavedSearchModel | None:
        """Update the match count for a specific saved search."""
        db_search = self.get(search_id)
        if not db_search:
            return None

        self._update_match_count(db_search)
        self.db.commit()
        self.db.refresh(db_search)

        return db_search

    def update_all_match_counts(self) -> dict[str, int]:
        """Update match counts for all active saved searches."""
        active_searches = self.db.query(SavedSearchModel).filter(SavedSearchModel.is_active).all()

        updated = 0
        failed = 0

        for search in active_searches:
            try:
                self._update_match_count(search)
                updated += 1
            except Exception:
                failed += 1

        self.db.commit()

        return {"updated": updated, "failed": failed}

    def _update_match_count(self, search: SavedSearchModel) -> None:
        """Internal method to update match count for a saved search."""
        # Build query based on search parameters
        query = self.db.query(Item).join(Item.edition)

        # Apply text search
        if search.query:
            # Simple text search - in production, you'd use FTS
            query = query.filter(
                or_(
                    Item.title.contains(search.query),
                    Item.text.contains(search.query)
                )
            )

        # Apply item type filters
        if search.item_types:
            query = query.filter(Item.item_type.in_(search.item_types))

        # Apply date filters
        if search.date_from:
            query = query.filter(Edition.edition_date >= search.date_from)

        if search.date_to:
            query = query.filter(Edition.edition_date <= search.date_to)

        # Count matches
        match_count = query.count()

        # Update search record
        search.match_count = match_count
        search.last_run = datetime.utcnow()
