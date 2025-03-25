from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging
from models import SessionLocal, City, CityFact
from sqlalchemy.orm import Session
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CityRequest(BaseModel):
    name: str

class CityFactsResponse(BaseModel):
    name: str
    facts: str

class CityFactsRequest(BaseModel):
    name: str
    facts: str

@app.get("/city/{city_name}", response_model=CityFactsResponse)
async def get_city_facts(city_name: str, db: Session = Depends(get_db)):
    """
    Retrieve facts about a city from the database if available.
    """
    logger.info(f"Fetching facts for city: {city_name}")
    
    db_city = db.query(City).filter(City.name.ilike(city_name)).first()
    
    if not db_city:
        logger.info(f"City {city_name} not found in database")
        return CityFactsResponse(name=city_name, facts="")
    
    facts = db.query(CityFact).filter(CityFact.city_id == db_city.id).all()
    
    if not facts:
        logger.info(f"No facts found for city {city_name}")
        return CityFactsResponse(name=city_name, facts="")
    
    facts_text = f"Facts about {db_city.name}:\n\n"
    for fact in facts:
        facts_text += f"{fact.fact_type}: {fact.fact_value}\n"
    
    return CityFactsResponse(name=db_city.name, facts=facts_text)

@app.get("/city/gemini/{city_name}", response_model=CityFactsResponse)
async def get_city_facts_from_gemini(city_name: str):
    """
    Retrieve facts about a city from the Gemini API.
    """
    logger.info(f"Fetching facts for city {city_name} from Gemini API")
    
    try:
        prompt = f"""
        You are a knowledgeable assistant who provides interesting facts about different cities.
        Provide information about the city {city_name} in the following format:
        
        1. First state the name of the city clearly.
        2. Then provide its population if available.
        3. Then provide five interesting points about its history, culture, economy, or other notable aspects.
        
        Present the information in a clear, numbered list format with each fact on a new line.
        """
        
        response = model.generate_content(prompt)
        
        if not response.text:
            raise HTTPException(status_code=500, detail="Failed to get response from Gemini API")
        
        return CityFactsResponse(name=city_name, facts=response.text)
    
    except Exception as e:
        logger.error(f"Error fetching from Gemini API: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch city facts from Gemini API: {str(e)}"
        )

@app.post("/city", response_model=CityFactsResponse)
async def save_city_facts(request: CityFactsRequest, db: Session = Depends(get_db)):
    """
    Save city facts to the database.
    """
    logger.info(f"Saving facts for city: {request.name}")
    
    try:
        db_city = db.query(City).filter(City.name.ilike(request.name)).first()
        
        if not db_city:
            db_city = City(name=request.name)
            db.add(db_city)
            db.commit()
            db.refresh(db_city)
        
        facts_list = request.facts.split('\n')
        
        db.query(CityFact).filter(CityFact.city_id == db_city.id).delete()
        
        for fact_line in facts_list:
            if fact_line.strip():
                if ':' in fact_line:
                    fact_type, fact_value = fact_line.split(':', 1)
                    fact_type = fact_type.strip()
                    fact_value = fact_value.strip()
                else:
                    fact_type = "Fact"
                    fact_value = fact_line.strip()
                
                db_fact = CityFact(
                    city_id=db_city.id,
                    fact_type=fact_type,
                    fact_value=fact_value
                )
                db.add(db_fact)
        
        db.commit()
        
        return CityFactsResponse(name=db_city.name, facts=request.facts)
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving city facts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save city facts: {str(e)}"
        )

@app.post("/city/display", response_model=CityFactsResponse)
async def display_city_facts(request: CityFactsRequest):
    """
    Format city facts for beautiful display.
    """
    logger.info(f"Formatting facts for display for city: {request.name}")
    
    try:
        formatted_facts = f"✨ {request.name.upper()} ✨\n\n"
        formatted_facts += "Here are some interesting facts:\n\n"
        
        facts_lines = [line.strip() for line in request.facts.split('\n') if line.strip()]
        for i, line in enumerate(facts_lines, 1):
            formatted_facts += f"{i}. {line}\n"
        
        return CityFactsResponse(name=request.name, facts=formatted_facts)
    
    except Exception as e:
        logger.error(f"Error formatting city facts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to format city facts: {str(e)}"
        )