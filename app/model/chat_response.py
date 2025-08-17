from pydantic import BaseModel

class ChatResponse(BaseModel):
    message: str
    phone: str
    execution_time: str
