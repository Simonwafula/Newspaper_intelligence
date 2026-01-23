import csv
import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.auth import get_admin_user
from app.db.database import get_db
from app.models import Item
from app.schemas import ItemSubtype, ItemType

router = APIRouter()


@router.get("/jobs.csv")
async def export_jobs_csv(
    date_from: str = None,
    date_to: str = None,
    sector: str = None,
    format: str = "csv",
    db: Session = Depends(get_db),
    _user_auth = Depends(get_admin_user)
):
    """Export all job listings with enhanced structured fields."""
    from datetime import datetime


    # Build query for job classifieds
    query = db.query(Item).filter(
        Item.item_type == ItemType.CLASSIFIED,
        Item.subtype == ItemSubtype.JOB
    )

    # Add date filters
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Item.created_at >= date_from_obj)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO format.") from e

    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Item.created_at <= date_to_obj)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO format.") from e

    # Get items
    items = query.order_by(Item.created_at.desc()).all()

    # Generate CSV with enhanced structure
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "edition_id", "page_number", "title", "text",
        "job_title", "employer", "salary_range", "sector", "created_at"
    ])

    for item in items:
        # Get structured data
        structured_data = item.structured_data or {}
        job_title = structured_data.get('job_title', '')
        employer = structured_data.get('employer', '')
        salary_min = structured_data.get('salary_min', '')
        salary_max = structured_data.get('salary_max', '')
        salary_range = f"{salary_min}-{salary_max}" if salary_min and salary_max else f"{salary_min or ''}"
        sector = structured_data.get('sector', [''])
        sector_str = ', '.join(sector) if isinstance(sector, list) else str(sector)

        writer.writerow([
            str(item.edition_id), str(item.page_number),
            (item.title or "").replace('\n', ' ').strip(),
            (item.text or "")[:500] + "..." if len(item.text or "") > 500 else (item.text or ""),
            job_title, employer, salary_range, sector_str,
            item.created_at.isoformat() if item.created_at else ""
        ])

    filename = f"jobs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/tenders.csv")
async def export_tenders_csv(
    date_from: str = None,
    date_to: str = None,
    category: str = None,
    format: str = "csv",
    db: Session = Depends(get_db),
    _user_auth = Depends(get_admin_user)
):
    """Export all tender notices with enhanced structured fields."""
    from datetime import datetime


    # Build query for tender classifieds
    query = db.query(Item).filter(
        Item.item_type == ItemType.CLASSIFIED,
        Item.subtype == ItemSubtype.TENDER
    )

    # Add date filters
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Item.created_at >= date_from_obj)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO format.") from e

    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Item.created_at <= date_to_obj)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO format.") from e

    # Get items
    items = query.order_by(Item.created_at.desc()).all()

    # Generate CSV with enhanced structure
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "edition_id", "page_number", "title", "text",
        "tender_reference", "issuer", "estimated_value", "category", "created_at"
    ])

    for item in items:
        # Get structured data
        structured_data = item.structured_data or {}
        tender_ref = structured_data.get('tender_reference', '')
        issuer = structured_data.get('issuer', '')
        value = structured_data.get('estimated_value', '')
        currency = structured_data.get('currency', '')
        estimated_value = f"{value} {currency}" if value and currency else f"{value or ''}"
        category = structured_data.get('category', [''])
        category_str = ', '.join(category) if isinstance(category, list) else str(category)

        writer.writerow([
            str(item.edition_id), str(item.page_number),
            (item.title or "").replace('\n', ' ').strip(),
            (item.text or "")[:500] + "..." if len(item.text or "") > 500 else (item.text or ""),
            tender_ref, issuer, estimated_value, category_str,
            item.created_at.isoformat() if item.created_at else ""
        ])

    filename = f"tenders_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
