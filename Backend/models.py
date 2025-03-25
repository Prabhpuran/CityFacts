# models.py
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel

SQLALCHEMY_DATABASE_URL = "sqlite:///./city_facts.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class City(Base):
    __tablename__ = "cities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    facts = relationship("CityFact", back_populates="city")

class CityFact(Base):
    __tablename__ = "city_facts"
    
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"))
    fact_type = Column(String)
    fact_value = Column(Text)
    
    city = relationship("City", back_populates="facts")

Base.metadata.create_all(bind=engine)

# Pydantic models for request/response validation
class CityBase(BaseModel):
    name: str

class CityCreate(CityBase):
    pass

class CityResponse(CityBase):
    id: int
    
    class Config:
        orm_mode = True

class FactBase(BaseModel):
    fact_type: str
    fact_value: str

class FactCreate(FactBase):
    pass

class FactResponse(FactBase):
    id: int
    city_id: int
    
    class Config:
        orm_mode = True

class CityWithFacts(CityResponse):
    facts: list[FactResponse] = []