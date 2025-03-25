import logging
import os

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from models import City, CityFact, SessionLocal
from pydantic import BaseModel
from sqlalchemy.orm import Session

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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBH3_osKZxTpL1Ci3gG0Xfvx80qtWDS08A")
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
    # cache 
    db_city = db.query(City).filter(City.name.ilike(city_name)).first()

    facts = []

       
    if db_city:
        facts = db.query(CityFact).filter(CityFact.city_id == db_city.id).all()
    
    if not facts:
        logger.info(f"No facts found for city {city_name}")
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
            
            facts = response.text
            
            # return CityFactsResponse(name=city_name, facts=response.text)
            try:
                db_city = db.query(City).filter(City.name.ilike(city_name)).first()
                
                if not db_city:
                    db_city = City(name=city_name)
                    db.add(db_city)
                    db.flush()
                
                facts_list = response.text.split('\n')
                
            
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
                
                return JSONResponse({"name": db_city.name, "facts": facts})
            
            except Exception as e:
                db.rollback()
                logger.error(f"Error saving city facts: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save city facts: {str(e)}"
                )
        
        except Exception as e:
            logger.error(f"Error fetching from Gemini API: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch city facts from Gemini API: {str(e)}"
            )
        

    if not db_city:
        return HTTPException(status_code=500, detail="something went wrong")
        
    
    facts_text = f"Facts about {db_city.name}:\n\n"
    for fact in facts:
        facts_text += f"{fact.fact_type}: {fact.fact_value}\n"
    
    return CityFactsResponse(name=str(db_city.name), facts=facts_text)




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4050)