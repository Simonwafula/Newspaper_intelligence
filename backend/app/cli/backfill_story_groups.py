import logging

from app.db.database import SessionLocal
from app.models import Edition
from app.services.story_grouping import persist_story_groups

logger = logging.getLogger(__name__)


def main() -> int:
    db = SessionLocal()
    try:
        editions = db.query(Edition).filter(Edition.status.in_(["READY", "ARCHIVED"])).all()
        total_groups = 0
        for edition in editions:
            try:
                grouped = persist_story_groups(db, edition.id)
                total_groups += grouped
                logger.info("Grouped edition %s with %s groups", edition.id, grouped)
            except Exception as exc:
                logger.warning("Failed to group edition %s: %s", edition.id, exc)
        logger.info("Backfill complete. Total groups: %s", total_groups)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
