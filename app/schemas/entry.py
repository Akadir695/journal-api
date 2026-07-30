from pydantic import BaseModel, Field, field_validator
from datetime import date
class EntryCreate(BaseModel):             
    title: str = Field(min_length=1, max_length=200)                              
    content: str = Field(min_length=1, max_length=2000)             
    mood: int = Field(ge=1, le=5)                              
    entry_date: date  
    @field_validator("title", "content")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("cannot be blank")
        return stripped
    
 
      
      
    
      
  


   
                           