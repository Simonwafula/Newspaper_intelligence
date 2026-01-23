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

        # Job title patterns
        job_title_patterns = [
            r'(?:vacancy|position|role|job title|we are hiring|looking for)\s*[:#]?\s*([^\n,]+)',
            r'\b(Manager|Director|Officer|Executive|Supervisor|Coordinator|Specialist|Analyst|Developer|Engineer|Accountant|Consultant|Representative|Agent|Assistant)\b',
            r'\b(Senior|Junior|Lead|Chief|Head|Deputy|Assistant|Associate)\s+(Manager|Director|Officer|Executive|Supervisor|Coordinator|Specialist|Analyst|Developer|Engineer|Accountant|Consultant|Representative|Agent|Assistant)\b'
        ]
        
        for pattern in job_title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                job_title = match.group(1) if match.groups() else match.group(0)
                details['job_title'] = job_title.strip()
                break

        # Employer/Company patterns
        employer_patterns = [
            r'(?:company|organization|employer)\s*[:#]?\s*([^\n,]+)',
            r'\bat\s+([A-Z][a-zA-Z\s&]+)\b',
            r'(?:join|work\s+for)\s+([A-Z][a-zA-Z\s&]+)\b'
        ]
        
        for pattern in employer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                details['employer'] = match.group(1).strip()
                break

        # Salary/compensation patterns
        salary_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:per\s*)?(?:month|year|annum|annually|pa|p\.a\.)',  # $50,000 per year
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:KES|TSH|UGX|TZS)\s*(?:per\s*)?(?:month|year|annum)',  # 50,000 KES per month
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*-\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:\$|KES|TSH|UGX|TZS)',  # 30,000 - 50,000 KES
            r'salary\s*[:#]?\s*([^\n,]+)',
            r'compensation\s*[:#]?\s*([^\n,]+)'
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.groups() and len(match.groups()) >= 2:
                    # Salary range
                    salary_min = float(match.group(1).replace(',', ''))
                    salary_max = float(match.group(2).replace(',', ''))
                    details['salary_min'] = salary_min
                    details['salary_max'] = salary_max
                elif match.groups():
                    # Single salary
                    salary = float(match.group(1).replace(',', ''))
                    details['salary_min'] = salary
                    details['salary_max'] = salary
                else:
                    # Text salary description
                    details['salary_description'] = match.group(0).strip()
                
                # Extract currency
                salary_text = match.group(0).upper()
                if '$' in salary_text:
                    details['salary_currency'] = 'USD'
                elif 'KES' in salary_text:
                    details['salary_currency'] = 'KES'
                elif 'TSH' in salary_text:
                    details['salary_currency'] = 'TSH'
                elif 'UGX' in salary_text:
                    details['salary_currency'] = 'UGX'
                elif 'TZS' in salary_text:
                    details['salary_currency'] = 'TZS'
                else:
                    details['salary_currency'] = 'KES'  # Default
                break

        # Experience requirements
        experience_patterns = [
            r'(\d+)\+?\s*(?:years?|yr)\s+(?:of\s+)?(?:experience|exp)',
            r'(\d+)\s*-\s*(\d+)\s*(?:years?|yr)\s+(?:of\s+)?(?:experience|exp)',
            r'experience\s*[:#]?\s*(\d+)',
            r'(?:minimum|required)\s*(?:years?\s*of\s*)?experience\s*[:#]?\s*(\d+)'
        ]
        
        for pattern in experience_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.groups() and len(match.groups()) >= 2:
                    # Experience range
                    details['experience_years_min'] = int(match.group(1))
                    details['experience_years_max'] = int(match.group(2))
                elif match.groups():
                    # Single experience
                    details['experience_years'] = int(match.group(1))
                    details['experience_years_min'] = int(match.group(1))
                    details['experience_years_max'] = int(match.group(1))
                break

        # Sector/Industry patterns
        sector_patterns = [
            r'\b(IT|Information Technology|Software|Banking|Finance|Healthcare|Education|Manufacturing|Retail|Hospitality|Construction|Agriculture|Government|NGO|Telecommunications|Media|Marketing|Sales|Logistics|Human Resources|Legal|Engineering|Accounting)\b',
            r'(?:sector|industry)\s*[:#]?\s*([^\n,]+)'
        ]
        
        sectors = []
        for pattern in sector_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                sectors.append(match.strip())
        
        if sectors:
            details['sector'] = list(set(sectors))

        # Skills and qualifications
        skills_patterns = [
            r'\b((?:experience|proficiency|knowledge|skill)\s+(?:in|of|with)\s+[^,.\n]+)',
            r'\b(Python|Java|JavaScript|TypeScript|C\+\+|C#|SQL|Excel|Word|PowerPoint|Salesforce|SAP|Oracle|AWS|Azure|Google Cloud|Docker|Kubernetes|React|Angular|Vue|Node\.js|Django|Flask|Spring|\.NET|PHP|Ruby|Swift|Kotlin)\b',
            r'\b((?:communication|teamwork|leadership|problem[-\s]?solving|analytical|project management|time management|creativity|adaptability|critical thinking|customer service|negotiation|presentation)\s*(?:skills?|abilities?))\b'
        ]

        skills = []
        for pattern in skills_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                skills.append(match.strip())

        if skills:
            details['qualifications'] = list(set(skills))

        # Degree/education requirements
        education_patterns = [
            r'\b(Bachelor|Master|PhD|Doctorate|MBA|BSc|MSc|BA|MA|BCom|MCom|BEng|MEng|Diploma|Certificate)\s*(?:in|of)?\s*([^\n,]*)',
            r'\b(degree|qualification|education)\s*[:#]?\s*([^\n,]+)'
        ]
        
        education = []
        for pattern in education_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    education_str = f"{match[0]} {'in ' + match[1] if match[1] else ''}".strip()
                else:
                    education_str = match.strip()
                education.append(education_str)
        
        if education:
            details['education_requirements'] = list(set(education))

        # Deadline patterns
        deadline_patterns = [
            r'(?:deadline|closing date|apply by|submit by|last date)\s*[:#]?\s*([^\n,]+)',
            r'(?:application\s*)?(?:deadline|closing)\s*(?:on|by|before)\s*([^\n,]+)'
        ]
        
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                details['application_deadline'] = match.group(1).strip()
                break

        # Work location
        location_patterns = [
            r'\b(Remote|Work from Home|WFH|Hybrid|On-site|Office based)\b',
            r'(?:location|workplace|office)\s*[:#]?\s*([^\n,]+)',
            r'\bat\s+([A-Z][a-zA-Z\s]+)\s*(?:office|branch)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.groups():
                    details['work_location'] = match.group(1).strip()
                else:
                    details['work_mode'] = match.group(0).strip()
                break

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
        tender_ref_patterns = [
            r'(?:tender\s*(?:no\.?|ref\.?|reference|number)\s*[:#]?\s*)([A-Z0-9-/]+)',
            r'\b([A-Z]{2,4}\d{4,8}[-/]\d{3,4})\b',  # Common format like KE2024-001
            r'reference\s*[:#]?\s*([A-Z0-9-/]+)',
            r'ref\.?\s*[:#]?\s*([A-Z0-9-/]+)'
        ]
        
        for pattern in tender_ref_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                details['tender_reference'] = match.group(1).strip()
                break

        # Issuing organization
        issuer_patterns = [
            r'(?:issued\s*by|from|organization|company|ministry|department|authority)\s*[:#]?\s*([^,\n]+)',
            r'\b([A-Z][a-zA-Z\s&]{5,})\b(?:\s+is\s+(?:inviting|calling|requesting))',
            r'(?:inviting|calling|requesting)\s+(?:bids|proposals|applications)\s+from\s+([^,\n]+)'
        ]
        
        for pattern in issuer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                details['issuer'] = match.group(1).strip()
                break

        # Tender title
        title_patterns = [
            r'(?:tender\s*title|subject|project)\s*[:#]?\s*([^\n]+)',
            r're\s*:\s*([^\n]+)',
            r'subject\s*:\s*([^\n]+)'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                details['title'] = match.group(1).strip()
                break

        # Category/sector
        category_patterns = [
            r'(?:category|sector|industry|field)\s*[:#]?\s*([^\n,]+)',
            r'\b(supplies|services|construction|works|consultancy|training|maintenance|repair|IT|software|hardware|furniture|vehicles|equipment)\b'
        ]
        
        categories = []
        for pattern in category_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                categories.append(match.strip())
        
        if categories:
            details['category'] = list(set(categories))

        # Estimated value
        value_patterns = [
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:million|billion|thousand)?',
            r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:KES|TSH|UGX|TZS|USD)\s*(?:million|billion|thousand)?',
            r'(?:estimated\s*)?(?:value|cost|price|budget|contract\s*value)\s*[:#]?\s*([^\n,]+)',
            r'(?:budget|price|cost)\s*[:#]?\s*([^\n,]+)'
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value_text = match.group(0) if not match.groups() else match.group(1)
                
                # Extract numeric value
                numeric_match = re.search(r'([\d,]+(?:\.\d{2})?)', value_text)
                if numeric_match:
                    value = float(numeric_match.group(1).replace(',', ''))
                    
                    # Handle multipliers
                    if 'million' in value_text.lower():
                        value *= 1000000
                    elif 'billion' in value_text.lower():
                        value *= 1000000000
                    elif 'thousand' in value_text.lower():
                        value *= 1000
                    
                    details['estimated_value'] = value
                    
                    # Extract currency
                    if '$' in value_text or 'USD' in value_text.upper():
                        details['currency'] = 'USD'
                    elif 'KES' in value_text.upper():
                        details['currency'] = 'KES'
                    elif 'TSH' in value_text.upper():
                        details['currency'] = 'TSH'
                    elif 'UGX' in value_text.upper():
                        details['currency'] = 'UGX'
                    elif 'TZS' in value_text.upper():
                        details['currency'] = 'TZS'
                    else:
                        details['currency'] = 'USD'  # Default
                break

        # Deadline
        deadline_patterns = [
            r'(?:deadline|closing\s*date|submission\s*deadline|bid\s*closing)\s*[:#]?\s*([^\n,]+)',
            r'(?:submit|send|deliver)\s*(?:bids|proposals|documents)\s*(?:by|before|on)\s*([^\n,]+)',
            r'closes?\s*(?:on|at)\s*([^\n,]+)'
        ]
        
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                details['deadline'] = match.group(1).strip()
                break

        # Eligibility criteria
        eligibility_patterns = [
            r'(?:eligibility|requirements|criteria|qualifications?)\s*[:#]?\s*([^\n]+)',
            r'(?:must\s*have|required|should\s*be)\s+([^,\n]+)',
            r'(?:bidder|applicant)\s*(?:must|should)\s+([^,\n]+)'
        ]
        
        eligibility = []
        for pattern in eligibility_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                eligibility.append(match.strip())
        
        if eligibility:
            details['eligibility'] = eligibility

        # Contact information
        contact_patterns = [
            r'(?:contact|inquiries|queries|clarifications?)\s*[:#]?\s*([^\n,]+)',
            r'(?:for\s+more\s+information|contact\s+us)\s*[:#]?\s*([^\n,]+)',
            r'(?:person|officer)\s*[:#]?\s*([^\n,]+)',
            r'(?:email|phone|tel|mobile)\s*[:#]?\s*([^\n,]+)'
        ]
        
        contact_info = []
        for pattern in contact_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                contact_info.append(match.strip())
        
        if contact_info:
            details['contact'] = contact_info

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
