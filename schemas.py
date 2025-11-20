"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Photo sorter app schemas

class Photo(BaseModel):
    """
    Photos collection schema
    Collection name: "photo"
    """
    filename: str = Field(..., description="Stored file name")
    url: str = Field(..., description="Public URL to access the photo")
    place: Optional[str] = Field(None, description="Place/location label")
    year: Optional[int] = Field(None, description="Year extracted from EXIF or provided")
    people: List[str] = Field(default_factory=list, description="Tagged people names")
    taken_at: Optional[datetime] = Field(None, description="Date and time photo was taken")
    gps_lat: Optional[float] = Field(None, description="Latitude from EXIF GPS if available")
    gps_lon: Optional[float] = Field(None, description="Longitude from EXIF GPS if available")
    notes: Optional[str] = Field(None, description="Optional notes")

class Person(BaseModel):
    """
    People collection schema
    Collection name: "person"
    """
    name: str = Field(..., description="Person name")
    alias: Optional[str] = Field(None, description="Alternate name or nickname")
    photo_count: int = Field(0, description="How many photos this person appears in")
