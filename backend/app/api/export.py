import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Edition, Item
from app.schemas import ItemSubtype, ItemType

router = APIRouter()


def flatten_structured_data(structured_json: Any) -> dict[str, str]:
    """Flatten structured JSON data into readable string values."""
    if not structured_json:
        return {}

    flattened = {}

    for key, value in structured_json.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, list):
                    flattened[f"{key}_{sub_key}"] = ', '.join(str(item) for item in sub_value)
                else:
                    flattened[f"{key}_{sub_key}"] = str(sub_value)
        elif isinstance(value, list):
            flattened[key] = ', '.join(str(item) for item in value)
        else:
            flattened[key] = str(value)

    return flattened


def get_classifieds_csv_headers() -> list[str]:
    """Get headers for classifieds export with structured fields."""
    base_headers = ["page_number", "title", "text", "subtype"]

    # Structured data headers
    classifieds_headers = [
        "contact_phone_numbers",
        "contact_email_addresses",
        "price_amount",
        "price_currency",
        "price_negotiable",
        "dates_mentioned",
        "deadlines",
        "location_addresses",
        "location_cities",
        "property_type",
        "bedrooms",
        "bathrooms",
        "area_sqft",
        "skills_required",
        "qualifications",
        "tender_reference",
        "issuing_organization",
        "auction_date",
        "venue",
        "notice_type"
    ]

    return base_headers + classifieds_headers


def format_classifieds_row(item: Item) -> list[str]:
    """Format a classifieds item as a CSV row with structured fields."""
    # Flatten all structured data
    contact_data = flatten_structured_data(item.contact_info_json or {})
    price_data = flatten_structured_data(item.price_info_json or {})
    date_data = flatten_structured_data(item.date_info_json or {})
    location_data = flatten_structured_data(item.location_info_json or {})
    details_data = flatten_structured_data(item.classification_details_json or {})

    # Clean text for CSV
    title = (item.title or "").replace('\n', ' ').strip()
    text = (item.text or "").replace('\n', ' ').strip()

    # Limit text length
    if len(text) > 1000:
        text = text[:1000] + "..."

    return [
        str(item.page_number),
        title,
        text,
        item.subtype.value if item.subtype is not None else "",
        contact_data.get('phone_numbers', ''),
        contact_data.get('email_addresses', ''),
        price_data.get('amount', ''),
        price_data.get('currency', ''),
        price_data.get('negotiable', ''),
        date_data.get('dates_mentioned', ''),
        date_data.get('deadlines', ''),
        location_data.get('addresses', ''),
        location_data.get('cities', ''),
        details_data.get('property_type', ''),
        details_data.get('bedrooms', ''),
        details_data.get('bathrooms', ''),
        details_data.get('area_sqft', ''),
        details_data.get('skills_required', ''),
        details_data.get('qualifications', ''),
        details_data.get('tender_reference', ''),
        details_data.get('issuing_organization', ''),
        details_data.get('auction_date', ''),
        details_data.get('venue', ''),
        details_data.get('notice_type', '')
    ]


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
    For classifieds, includes structured data fields.
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

    # Determine headers based on item type
    if item_type == ItemType.CLASSIFIED:
        headers = get_classifieds_csv_headers()
        writer.writerow(headers)

        # Write classifieds data rows with structured fields
        for item in items:
            row = format_classifieds_row(item)
            writer.writerow(row)
    else:
        # Standard headers for stories and ads
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
                item.subtype.value if item.subtype is not None else ""
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

    Includes stories, ads, and classifieds. For classifieds, includes structured data fields.
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

    # Write header row - include all classifieds fields for comprehensive export
    headers = ["page_number", "item_type", "subtype", "title", "text"] + [
        "contact_phone_numbers", "contact_email_addresses", "price_amount", "price_currency",
        "price_negotiable", "dates_mentioned", "deadlines", "location_addresses", "location_cities",
        "property_type", "bedrooms", "bathrooms", "area_sqft", "skills_required",
        "qualifications", "tender_reference", "issuing_organization", "auction_date",
        "venue", "notice_type"
    ]
    writer.writerow(headers)

    # Write data rows
    for item in items:
        if str(item.item_type) == ItemType.CLASSIFIED:
            # Use classifieds formatting for structured data
            classifieds_row = format_classifieds_row(item)
            # Prepend basic fields
            row = [
                str(item.page_number),
                item.item_type.value,
                item.subtype.value if item.subtype is not None else "",
                classifieds_row[1],  # title (already formatted)
                classifieds_row[2],  # text (already formatted)
            ] + classifieds_row[4:]  # all structured fields (skip page, title, text, subtype)
        else:
            # Standard formatting for stories and ads
            title = (item.title or "").replace('\n', ' ').strip()
            text = (item.text or "").replace('\n', ' ').strip()

            # Limit text length for readability
            if len(text) > 1000:
                text = text[:1000] + "..."

            row = [
                str(item.page_number),
                item.item_type.value,
                item.subtype.value if item.subtype is not None else "",
                title,
                text
            ] + [''] * 21  # Empty structured fields for non-classifieds

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
