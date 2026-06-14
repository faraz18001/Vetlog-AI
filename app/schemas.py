from pydantic import BaseModel
from typing import List

# This tells FastAPI: "Expect a JSON object that contains a list of strings called 'messages'"
class IngestionPayload(BaseModel):
    messages: List[str]