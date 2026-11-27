# webapp/schemas/profile.py
from pydantic import BaseModel


class ProfileUpdateRequest(BaseModel):
    first_name: str
    last_name: str
