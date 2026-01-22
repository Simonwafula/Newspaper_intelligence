import logging
import re

logger = logging.getLogger(__name__)


class ClassifiedsIntelligence:
    """Extracts structured information from classified advertisements."""

    def __init__(self):
        # Pattern definitions for extracting structured information
        self.phone_patterns = [
            r'\b(?:\+?(\d{1,3})[-. ]?)?\(?(\d{3})\)?[-. ]?(\d{3})[-. ]?(\d{4})\b',
            r'\b(\d{3}[-. ]?\d{3}[-. ]?\d{4})\b',
            r'\b(\d{10})\b'
        ]

        self.email_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ]

        self.price_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|KES|TSH|UGX|TZS)',  # 1,234.56 USD
            r'(\d+(?:,\d+)*)\s*(?:shillings|shs|/-)',  # 1,234 shillings
            r'KES\s*(\d+(?:,\d+)*)',  # KES 1,234
            r'TSH\s*(\d+(?:,\d+)*)',  # TSH 1,234
            r'UGX\s*(\d+(?:,\d+)*)',  # UGX 1,234
        ]

        self.date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # DD/MM/YYYY
            r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',  # YYYY/MM/DD
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',  # Jan 15, 2024
            r'\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',  # 15 Jan 2024
            r'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',  # Monday, 15 Jan 2024
        ]

        self.location_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*[A-Z]{2,3}\b',  # Nairobi, KE
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr)\b',
            r'\bPlot\s+No\.?\s*\d+\b',
            r'\bHouse\s+No\.?\s*\d+\b',
            r'\bApartment\s+\d+\b',
            r'\bFlat\s+\d+\b',
        ]

    def extract_contact_info(self, text: str) -> dict[str, list[str]]:
        """Extract phone numbers and email addresses."""
        contact_info = {
            'phone_numbers': [],
            'email_addresses': []
        }

        # Extract phone numbers
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Handle grouped pattern matches
                    phone = '-'.join(filter(None, match))
                else:
                    phone = match

                # Normalize phone format
                if re.match(r'^\d{10}$', phone):
                    phone = f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"

                if phone not in contact_info['phone_numbers']:
                    contact_info['phone_numbers'].append(phone)

        # Extract email addresses
        for pattern in self.email_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match not in contact_info['email_addresses']:
                    contact_info['email_addresses'].append(match)

        return contact_info if (contact_info['phone_numbers'] or contact_info['email_addresses']) else {}

    def extract_price_info(self, text: str) -> dict[str, any]:
        """Extract price information."""
        price_info = {}

        for pattern in self.price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    amount_str = match[0] if match[0] else match[1]
                else:
                    amount_str = match

                try:
                    # Clean and convert to float
                    amount = float(amount_str.replace(',', ''))

                    # Determine currency
                    currency = 'USD'  # Default
                    if 'KES' in text.upper():
                        currency = 'KES'
                    elif 'TSH' in text.upper():
                        currency = 'TSH'
                    elif 'UGX' in text.upper():
                        currency = 'UGX'
                    elif 'SHILLINGS' in text.upper() or 'SHS' in text.upper() or '/-' in text:
                        currency = 'KES'  # Default East African
                    elif '$' in text:
                        currency = 'USD'

                    # Check if negotiable
                    negotiable = any(word in text.lower() for word in ['negotiable', 'ono', 'or nearest offer', 'best offer'])

                    price_info = {
                        'amount': amount,
                        'currency': currency,
                        'negotiable': negotiable
                    }
                    break  # Take first reasonable match

                except ValueError:
                    continue

        return price_info

    def extract_date_info(self, text: str) -> dict[str, list[str]]:
        """Extract date information."""
        date_info = {
            'dates_mentioned': [],
            'deadlines': []
        }

        # Extract all dates
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    date_str = ' '.join(filter(None, match))
                else:
                    date_str = match

                if date_str not in date_info['dates_mentioned']:
                    date_info['dates_mentioned'].append(date_str)

        # Look for deadline indicators
        deadline_keywords = ['deadline', 'closing date', 'apply by', 'submit by', 'last date']
        for keyword in deadline_keywords:
            pattern = f'{keyword}[:\\s]*([^\\n]+)'
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Try to extract date from the context
                for date_pattern in self.date_patterns:
                    date_match = re.search(date_pattern, match)
                    if date_match:
                        date_str = date_match.group(0)
                        if date_str not in date_info['deadlines']:
                            date_info['deadlines'].append(date_str)

        return date_info if (date_info['dates_mentioned'] or date_info['deadlines']) else {}

    def extract_location_info(self, text: str) -> dict[str, list[str]]:
        """Extract location information."""
        location_info = {
            'addresses': [],
            'cities': [],
            'landmarks': []
        }

        # Extract addresses and locations
        for pattern in self.location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    location = match[0] if match[0] else match[1]
                else:
                    location = match

                if 'Street' in match or 'Avenue' in match or 'Road' in match:
                    if location not in location_info['addresses']:
                        location_info['addresses'].append(location)
                elif 'Plot' in match or 'House' in match or 'Apartment' in match or 'Flat' in match:
                    if location not in location_info['addresses']:
                        location_info['addresses'].append(location)
                else:
                    if location not in location_info['cities']:
                        location_info['cities'].append(location)

        return location_info if (location_info['addresses'] or location_info['cities']) else {}

    def extract_classification_details(self, text: str, subtype: str) -> dict[str, any]:
        """Extract subtype-specific structured information."""
        details = {}

        if subtype == 'JOB':
            details.update(self._extract_job_details(text))
        elif subtype == 'PROPERTY':
            details.update(self._extract_property_details(text))
        elif subtype == 'TENDER':
            details.update(self._extract_tender_details(text))
        elif subtype == 'AUCTION':
            details.update(self._extract_auction_details(text))
        elif subtype == 'NOTICE':
            details.update(self._extract_notice_details(text))

        return details

    def _extract_job_details(self, text: str) -> dict[str, any]:
        """Extract job-specific information."""
        details = {}

        # Look for common job keywords
        skills_patterns = [
            r'\b((?:experience|proficiency|knowledge|skill)\s+(?:in|of|with)\s+[^,.\n]+)',
            r'\b(\b(?:Python|Java|JavaScript|C\+\+|SQL|Excel|Word|PowerPoint)\b)'
        ]

        skills = []
        for pattern in skills_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                skills.append(match.strip())

        if skills:
            details['skills_required'] = list(set(skills))

        # Look for qualifications
        qualification_patterns = [
            r'\b(?:bachelor|master|phd|degree|diploma|certificate)[^,.\n]*',
            r'\b(?:years?|year)\s+(?:of\s+)?experience[^,.\n]*'
        ]

        qualifications = []
        for pattern in qualification_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                qualifications.append(match.strip())

        if qualifications:
            details['qualifications'] = list(set(qualifications))

        return details

    def _extract_property_details(self, text: str) -> dict[str, any]:
        """Extract property-specific information."""
        details = {}

        # Property type
        property_types = ['apartment', 'house', 'bungalow', 'mansion', 'flat', 'studio', 'plot', 'land']
        for prop_type in property_types:
            if re.search(rf'\b{prop_type}\b', text, re.IGNORECASE):
                details['property_type'] = prop_type
                break

        # Bedrooms
        bedroom_match = re.search(r'(\d+)\s*(?:bedroom|bed|br)', text, re.IGNORECASE)
        if bedroom_match:
            details['bedrooms'] = int(bedroom_match.group(1))

        # Bathrooms
        bathroom_match = re.search(r'(\d+)\s*(?:bathroom|bath|br)', text, re.IGNORECASE)
        if bathroom_match:
            details['bathrooms'] = int(bathroom_match.group(1))

        # Area
        area_match = re.search(r'(\d+)\s*(?:sq\s*ft|square\s*feet|m2|sqm)', text, re.IGNORECASE)
        if area_match:
            details['area_sqft'] = int(area_match.group(1))

        return details

    def _extract_tender_details(self, text: str) -> dict[str, any]:
        """Extract tender-specific information."""
        details = {}

        # Tender number/reference
        tender_ref_match = re.search(r'(?:tender\s*(?:no\.?|ref\.?|reference|number)\s*[:#]?\s*)([A-Z0-9-]+)', text, re.IGNORECASE)
        if tender_ref_match:
            details['tender_reference'] = tender_ref_match.group(1)

        # Company/organization
        company_match = re.search(r'(?:issued\s*by|from|organization)\s*[:#]?\s*([^,\n]+)', text, re.IGNORECASE)
        if company_match:
            details['issuing_organization'] = company_match.group(1).strip()

        return details

    def _extract_auction_details(self, text: str) -> dict[str, any]:
        """Extract auction-specific information."""
        details = {}

        # Auction date
        auction_date_match = re.search(r'(?:auction\s*date|date\s*of\s*auction)\s*[:#]?\s*([^\n,]+)', text, re.IGNORECASE)
        if auction_date_match:
            details['auction_date'] = auction_date_match.group(1).strip()

        # Auction venue
        venue_match = re.search(r'(?:venue|location|place)\s*[:#]?\s*([^\n,]+)', text, re.IGNORECASE)
        if venue_match:
            details['venue'] = venue_match.group(1).strip()

        return details

    def _extract_notice_details(self, text: str) -> dict[str, any]:
        """Extract notice-specific information."""
        details = {}

        # Notice type
        if re.search(r'\bobituary\b|\bdeath\b|\bpassed away\b', text, re.IGNORECASE):
            details['notice_type'] = 'obituary'
        elif re.search(r'\blost\b|\bmissing\b', text, re.IGNORECASE):
            details['notice_type'] = 'lost'
        elif re.search(r'\bfound\b', text, re.IGNORECASE):
            details['notice_type'] = 'found'
        else:
            details['notice_type'] = 'general'

        return details

    def process_classified(self, text: str, subtype: str) -> dict[str, any]:
        """
        Process classified text to extract all structured information.

        Returns a dictionary with all extracted structured data.
        """
        result = {
            'contact_info': self.extract_contact_info(text),
            'price_info': self.extract_price_info(text),
            'date_info': self.extract_date_info(text),
            'location_info': self.extract_location_info(text),
            'classification_details': self.extract_classification_details(text, subtype)
        }

        # Remove empty sections
        return {k: v for k, v in result.items() if v}


def create_classifieds_intelligence() -> ClassifiedsIntelligence:
    """Factory function to create ClassifiedsIntelligence instance."""
    return ClassifiedsIntelligence()
