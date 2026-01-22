import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Edition, Item
from app.schemas import ItemSubtype, ItemType

router = APIRouter()


@router.get("/edition/{edition_id}/export/{item_type}.csv")
async def export_items_csv(
    edition_id: int,
    item_type: ItemType,
    subtype: ItemSubtype | None = None,
    db: Session = Depends(get_db)
):
    """
    Export items from an edition as CSV file.

    Supports exporting stories, ads, or classifieds with optional subtype filtering.
    """
    # Verify edition exists
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")

    # Build query for items
    query = db.query(Item).filter(
        Item.edition_id == edition_id,
        Item.item_type == item_type
    )

    # Add subtype filter if provided
    if subtype:
        query = query.filter(Item.subtype == subtype)

    # Order by page number for logical flow
    items = query.order_by(Item.page_number, Item.id).all()

    # Generate CSV content
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    headers = ["page_number", "title", "text", "subtype"]
    writer.writerow(headers)

    # Write data rows
    for item in items:
        # Clean text for CSV (remove newlines and extra whitespace)
        title = (item.title or "").replace('\n', ' ').strip()
        text = (item.text or "").replace('\n', ' ').strip()

        # Limit text length for readability
        if len(text) > 1000:
            text = text[:1000] + "..."

        row = [
            item.page_number,
            title,
            text,
            item.subtype.value if item.subtype else ""
        ]
        writer.writerow(row)

    # Create response
    csv_content = output.getvalue()
    output.close()

    # Generate filename
    filename = f"{edition.newspaper_name}_{edition.edition_date.strftime('%Y-%m-%d')}_{item_type.value.lower()}"
    if subtype:
        filename += f"_{subtype.value.lower()}"
    filename += ".csv"

    # Clean filename for safe file system usage
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/edition/{edition_id}/export/all.csv")
async def export_all_items_csv(
    edition_id: int,
    db: Session = Depends(get_db)
):
    """
    Export all items from an edition as CSV file.

    Includes stories, ads, and classifieds with type and subtype information.
    """
    # Verify edition exists
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")

    # Get all items for the edition
    items = db.query(Item).filter(
        Item.edition_id == edition_id
    ).order_by(Item.page_number, Item.id).all()

    # Generate CSV content
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    headers = ["page_number", "item_type", "subtype", "title", "text"]
    writer.writerow(headers)

    # Write data rows
    for item in items:
        # Clean text for CSV (remove newlines and extra whitespace)
        title = (item.title or "").replace('\n', ' ').strip()
        text = (item.text or "").replace('\n', ' ').strip()

        # Limit text length for readability
        if len(text) > 1000:
            text = text[:1000] + "..."

        row = [
            item.page_number,
            item.item_type.value,
            item.subtype.value if item.subtype else "",
            title,
            text
        ]
        writer.writerow(row)

    # Create response
    csv_content = output.getvalue()
    output.close()

    # Generate filename
    filename = f"{edition.newspaper_name}_{edition.edition_date.strftime('%Y-%m-%d')}_all_items.csv"

    # Clean filename for safe file system usage
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
