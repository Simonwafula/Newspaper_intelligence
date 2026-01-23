"""
Seed categories utility script.
Populates the database with predefined topic categories.
"""

import os
import sys

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models import Category

DEFAULT_CATEGORIES = [
    {
        "name": "Economics & Finance",
        "slug": "economics-finance",
        "description": "Economic news, markets, finance, banking, and monetary policy",
        "color": "#10B981",  # Emerald
        "keywords": [
            "economy", "economic", "finance", "financial", "bank", "banking", "money",
            "market", "markets", "stock", "stocks", "share", "shares", "investment",
            "investing", "currency", "exchange", "trade", "trading", "budget", "tax",
            "inflation", "recession", "growth", "gdp", "interest", "rates", "credit",
            "debt", "loan", "loans", "asset", "portfolio", "fund", "funds"
        ],
        "sort_order": 1
    },
    {
        "name": "Politics & Government",
        "slug": "politics-government",
        "description": "Political news, government policies, elections, and governance",
        "color": "#EF4444",  # Red
        "keywords": [
            "politics", "political", "government", "governance", "election", "elections",
            "vote", "voting", "campaign", "candidate", "party", "parties", "policy",
            "policies", "parliament", "congress", "senate", "minister", "president",
            "governor", "mayor", "council", "committee", "bill", "legislation", "law",
            "court", "judicial", "constitution", "democracy", "reform", "administration"
        ],
        "sort_order": 2
    },
    {
        "name": "Business & Industry",
        "slug": "business-industry",
        "description": "Business news, corporate updates, industry trends, and commerce",
        "color": "#3B82F6",  # Blue
        "keywords": [
            "business", "businesses", "company", "companies", "corporate", "industry",
            "industries", "commercial", "enterprise", "enterprises", "firm", "firms",
            "corporation", "corporations", "startup", "startups", "entrepreneur",
            "entrepreneurship", "merger", "acquisition", "revenue", "profit", "sales",
            "marketing", "brand", "retail", "wholesale", "manufacturing", "production",
            "service", "services", "customer", "clients", "b2b", "b2c", "marketplace"
        ],
        "sort_order": 3
    },
    {
        "name": "Labor & Employment",
        "slug": "labor-employment",
        "description": "Employment news, job market, labor rights, and workforce issues",
        "color": "#F59E0B",  # Amber
        "keywords": [
            "labor", "employment", "employee", "employees", "employer", "employers",
            "job", "jobs", "work", "working", "workforce", "career", "careers",
            "hiring", "recruitment", "unemployment", "wage", "wages", "salary",
            "salaries", "income", "contract", "contracts", "union", "unions",
            "strike", "strikes", "benefits", "pension", "retirement", "training",
            "skills", "qualification", "qualifications", "vacancy", "vacancies"
        ],
        "sort_order": 4
    },
    {
        "name": "Social Issues",
        "slug": "social-issues",
        "description": "Social matters, community news, and societal challenges",
        "color": "#8B5CF6",  # Purple
        "keywords": [
            "social", "society", "community", "communities", "people", "public",
            "citizen", "citizens", "welfare", "health", "healthcare", "education",
            "housing", "poverty", "inequality", "rights", "human", "justice",
            "crime", "safety", "security", "environment", "climate", "sustainability",
            "culture", "cultural", "religion", "family", "youth", "elderly",
            "disability", "gender", "women", "children", "immigration", "diversity"
        ],
        "sort_order": 5
    },
    {
        "name": "Infrastructure & Development",
        "slug": "infrastructure-development",
        "description": "Infrastructure projects, urban development, and construction",
        "color": "#6366F1",  # Indigo
        "keywords": [
            "infrastructure", "development", "construction", "building", "buildings",
            "urban", "city", "cities", "town", "towns", "roads", "highways", "bridges",
            "transport", "transportation", "traffic", "airport", "airports", "railway",
            "railways", "water", "sanitation", "electricity", "power", "energy",
            "telecommunications", "internet", "housing", "estate", "real", "project",
            "projects", "contract", "contractor", "contractors", "tender", "tenders"
        ],
        "sort_order": 6
    },
    {
        "name": "Agriculture & Rural",
        "slug": "agriculture-rural",
        "description": "Agricultural news, farming, rural development, and food security",
        "color": "#84CC16",  # Lime
        "keywords": [
            "agriculture", "farming", "farm", "farms", "farmer", "farmers", "crop",
            "crops", "livestock", "cattle", "dairy", "poultry", "fishing", "irrigation",
            "rural", "village", "villages", "food", "food security", "harvest",
            "seeds", "fertilizer", "pesticide", "machinery", "equipment", "subsidy",
            "market", "prices", "commodity", "commodities", "organic", "sustainable",
            "agribusiness", "forestry", "horticulture", "aquaculture"
        ],
        "sort_order": 7
    },
    {
        "name": "Legal & Notices",
        "slug": "legal-notices",
        "description": "Legal announcements, court notices, and official government notices",
        "color": "#6B7280",  # Gray
        "keywords": [
            "legal", "law", "court", "courts", "judge", "judgment", "judiciary",
            "notice", "notices", "announcement", "announcements", "official", "public",
            " gazette", "regulation", "regulations", "statute", "statutes", "act",
            "acts", "ordinance", "ordinances", "bylaw", "bylaws", "rule", "rules",
            "decree", "order", "orders", "summons", "warrant", "injunction", "appeal",
            "verdict", "sentence", "probation", "litigation", "lawsuit", "case", "cases"
        ],
        "sort_order": 8
    },
    {
        "name": "Sports & Entertainment",
        "slug": "sports-entertainment",
        "description": "Sports news, entertainment, arts, culture, and leisure activities",
        "color": "#EC4899",  # Pink
        "keywords": [
            "sport", "sports", "game", "games", "match", "matches", "tournament",
            "tournaments", "competition", "competitions", "team", "teams", "player",
            "players", "athlete", "athletes", "coach", "coaching", "football", "soccer",
            "cricket", "rugby", "tennis", "basketball", "volleyball", "entertainment",
            "music", "concert", "concerts", "movie", "movies", "film", "films", "theater",
            "theatre", "drama", "comedy", "festival", "festivals", "arts", "culture"
        ],
        "sort_order": 9
    },
    {
        "name": "Science & Technology",
        "slug": "science-technology",
        "description": "Scientific research, technology news, innovation, and digital transformation",
        "color": "#14B8A6",  # Teal
        "keywords": [
            "science", "scientific", "research", "technology", "tech", "innovation",
            "innovative", "digital", "computer", "software", "hardware", "internet",
            "online", "data", "artificial", "intelligence", "ai", "machine", "learning",
            "automation", "robotics", "biotechnology", "engineering", "medical", "health",
            "pharmaceutical", "space", "satellite", "renewable", "energy", "electric",
            "vehicle", "automotive", "aviation", "telecommunications", "mobile", "phone",
            "smartphone", "app", "applications", "cybersecurity", "blockchain", "cloud"
        ],
        "sort_order": 10
    }
]


def seed_categories(db: Session) -> int:
    """Seed the database with default categories."""
    created_count = 0

    for cat_data in DEFAULT_CATEGORIES:
        # Check if category already exists
        existing = db.query(Category).filter(Category.slug == cat_data["slug"]).first()
        if existing:
            print(f"Category '{cat_data['name']}' already exists, skipping...")
            continue

        # Create new category
        category = Category(**cat_data)
        db.add(category)
        created_count += 1
        print(f"Created category: {cat_data['name']}")

    try:
        db.commit()
        print(f"\nSuccessfully created {created_count} categories.")
        return created_count
    except Exception as e:
        db.rollback()
        print(f"Error creating categories: {e}")
        return 0


def main():
    """Main function to run the seeding process."""
    print("Seeding default categories...")

    db = SessionLocal()
    try:
        count = seed_categories(db)
        if count > 0:
            print(f"✅ Successfully seeded {count} categories!")
        else:
            print("ℹ️ No new categories were created (they may already exist)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
