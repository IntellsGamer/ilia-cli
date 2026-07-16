from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select
from pydantic import BaseModel
import uvicorn

DATABASE_URL = "sqlite+aiosqlite:///./{{ project_name }}.db"
engine = create_async_engine(DATABASE_URL)
Session = async_sessionmaker(engine)

class Base(DeclarativeBase):
    pass

class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

class ItemCreate(BaseModel):
    name: str

class ItemRead(BaseModel):
    id: int
    name: str

app = FastAPI(title="{{ project_name }}", description="{{ description }}")

async def get_db():
    async with Session() as session:
        yield session

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/items", response_model=list[ItemRead])
async def list_items(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item))
    return result.scalars().all()

@app.post("/items", response_model=ItemRead)
async def create_item(data: ItemCreate, db: AsyncSession = Depends(get_db)):
    item = Item(name=data.name)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@app.get("/")
async def root():
    return {"project": "{{ project_name }}", "version": "{{ version }}"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port={{ port }}, reload=True)
