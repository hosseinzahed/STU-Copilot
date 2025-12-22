from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass

class BlogItem:
    """Data class to hold blog post information"""

    def __init__(self, id: str, title: str, url: str, published_date: str,
                 description: Optional[str] = None, tags: Optional[str] = None,
                 embedding: Optional[float] = None):
        self.id = id  # Unique identifier for the blog post
        self.title = title
        self.url = url
        self.description = description
        self.tags = tags
        self.published_date = published_date
        self.embedding = embedding

    def to_dict(self) -> Dict:
        """Convert the blog item to a dictionary for saving to CosmosDB"""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "tags": self.tags,
            "published_date": self.published_date,
            "embedding": self.embedding
        }

    @staticmethod
    def from_dict(data: Dict) -> 'BlogItem':
        """Create a BlogItem instance from a dictionary"""
        return BlogItem(
            id=data.get("id"),
            title=data.get("title"),
            url=data.get("url"),
            description=data.get("description"),
            tags=data.get("tags"),
            published_date=data.get("published_date"),
            embedding=data.get("embedding")
        )


class RepositoryInfo:
    """Data class to hold repository information"""

    def __init__(self, id: str, organization: str, name: str, url: str,
                 updated_at: str, stars_count: int, archived: bool,
                 description: Optional[str] = None, tags: Optional[str] = None,
                 embedding: Optional[float] = None):
        self.id = id  # Unique identifier for the repository
        self.organization = organization
        self.name = name
        self.url = url
        self.description = description
        self.tags = tags
        self.updated_at = updated_at
        self.stars_count = stars_count
        self.archived = archived
        self.embedding = embedding

    def to_dict(self) -> Dict:
        """Convert the repository info to a dictionary for saving to CosmosDB"""
        return {
            "id": self.id,
            "organization": self.organization,
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "tags": self.tags,
            "updated_at": self.updated_at,
            "stars_count": self.stars_count,
            "archived": self.archived,
            "embedding": self.embedding
        }

    @staticmethod
    def from_dict(data: Dict) -> 'RepositoryInfo':
        """Create a RepositoryInfo instance from a dictionary"""
        return RepositoryInfo(
            id=data.get("id"),
            organization=data.get("organization"),
            name=data.get("name"),
            url=data.get("url"),
            description=data.get("description"),
            tags=data.get("tags"),
            updated_at=data.get("updated_at"),
            stars_count=data.get("stars_count", 0),
            archived=data.get("archived", False),
            embedding=data.get("embedding")
        )


class SeismicContent:
    """Data class to hold Seismic content information"""

    @staticmethod
    def _to_iso_date(date_str: str) -> str:
        if not date_str or not isinstance(date_str, str):
            return date_str
        try:
            # Example: 'Jul 18, 2025 at 11:26 PM'
            dt = datetime.strptime(date_str, "%b %d, %Y at %I:%M %p")
            return dt.isoformat() + 'Z'
        except Exception:
            return date_str

    def __init__(self, id: str, name: str, url: str, version: str, version_creation_date: str, last_update: str, creation_date: str,
                 expiration_date: str, description: str, size: str, format: str, confidentiality: str, sales_stage: str,
                 audience: str, competitor: str, level: str, language: str, industry: str, initiative: str, segment: str,
                 content_sub_type: str, industry_sub_vertical: str, solution_area: str, content_group: str, products: str,
                 solution_play: str, industry_vertical: str, tags: Optional[str] = None, embedding: Optional[float] = None):
        self.id = id
        self.name = name
        self.url = url
        self.version = version
        self.version_creation_date = self._to_iso_date(version_creation_date)
        self.last_update = self._to_iso_date(last_update)
        self.creation_date = self._to_iso_date(creation_date)
        self.expiration_date = self._to_iso_date(expiration_date)
        self.description = description
        self.size = size
        self.format = format
        self.confidentiality = confidentiality
        self.sales_stage = sales_stage
        self.audience = audience
        self.competitor = competitor
        self.level = level
        self.language = language
        self.industry = industry
        self.initiative = initiative
        self.segment = segment
        self.content_sub_type = content_sub_type
        self.industry_sub_vertical = industry_sub_vertical
        self.solution_area = solution_area
        self.content_group = content_group
        self.products = products
        self.solution_play = solution_play
        self.industry_vertical = industry_vertical
        self.tags = tags
        self.embedding = embedding

    def to_dict(self) -> Dict:
        """Convert the SeismicContent to a dictionary for saving to CosmosDB"""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "version": self.version,
            "version_creation_date": self.version_creation_date,
            "last_update": self.last_update,
            "creation_date": self.creation_date,
            "expiration_date": self.expiration_date,
            "description": self.description,
            "size": self.size,
            "format": self.format,
            "confidentiality": self.confidentiality,
            "sales_stage": self.sales_stage,
            "audience": self.audience,
            "competitor": self.competitor,
            "level": self.level,
            "language": self.language,
            "industry": self.industry,
            "initiative": self.initiative,
            "segment": self.segment,
            "content_sub_type": self.content_sub_type,
            "industry_sub_vertical": self.industry_sub_vertical,
            "solution_area": self.solution_area,
            "content_group": self.content_group,
            "products": self.products,
            "solution_play": self.solution_play,
            "industry_vertical": self.industry_vertical,
            "tags": self.tags,
            "embedding": self.embedding
        }

    @staticmethod
    def from_dict(data: Dict) -> 'SeismicContent':
        """Create a SeismicContent instance from a dictionary"""
        return SeismicContent(
            id=data.get("id"),
            name=data.get("name"),
            url=data.get("url"),
            version=data.get("version"),
            version_creation_date=SeismicContent._to_iso_date(
                data.get("version_creation_date")),
            last_update=SeismicContent._to_iso_date(data.get("last_update")),
            creation_date=SeismicContent._to_iso_date(
                data.get("creation_date")),
            expiration_date=SeismicContent._to_iso_date(
                data.get("expiration_date")),
            description=data.get("description"),
            size=data.get("size"),
            format=data.get("format"),
            confidentiality=data.get("confidentiality"),
            sales_stage=data.get("sales_stage", "--"),
            audience=data.get("audience"),
            competitor=data.get("competitor", "--"),
            level=data.get("level"),
            language=data.get("language"),
            industry=data.get("industry", "--"),
            initiative=data.get("initiative", "--"),
            segment=data.get("segment"),
            content_sub_type=data.get("content_sub_type"),
            industry_sub_vertical=data.get("industry_sub_vertical", "--"),
            solution_area=data.get("solution_area"),
            content_group=data.get("content_group"),
            products=data.get("products", "--"),
            solution_play=data.get("solution_play", "--"),
            industry_vertical=data.get("industry_vertical", "--"),
            tags=data.get("tags"),
            embedding=data.get("embedding")
        )

@dataclass
class ComplianceItem:
    """Data class to hold compliance item information"""
    category: str
    title: str
    url: str
