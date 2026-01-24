import logging

from app.db.database import SessionLocal
from app.services.archive_service import archive_due_editions

logger = logging.getLogger(__name__)


def main() -> int:
    db = SessionLocal()
    try:
        archived_count = archive_due_editions(db)
        logger.info("Archived %s editions", archived_count)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
