from typing import Optional

from sqlmodel import Field, SQLModel, create_engine

from config import get_settings


class Card(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    serial_number: str
    card_number: str
    pin: str


engine = create_engine(get_settings().db_url)

SQLModel.metadata.create_all(engine)
