import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Query, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, String, Integer, DateTime, ForeignKey, Text, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./campus_care.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

SECRET_KEY = os.getenv("SECRET_KEY", "local-development-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60 * 12
INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "classroom-demo-key-change-me")

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    issue: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner: Mapped[User] = relationship(back_populates="tickets")

class Announcement(Base):
    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SignupIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TicketIn(BaseModel):
    issue: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=5, max_length=2000)
    location: str = Field(min_length=2, max_length=100)

class TicketPut(BaseModel):
    issue: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=5, max_length=2000)
    location: str = Field(min_length=2, max_length=100)

class TicketPatch(BaseModel):
    status: str = Field(pattern="^(open|in_progress|resolved|closed)$")

app = FastAPI(
    title="Campus Care API",
    description="A beginner-friendly college help desk API for learning HTTP, REST, authentication, API keys and databases.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing Bearer token. Please log in.")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", "0"))
    except (JWTError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return user

def ticket_dict(ticket: Ticket):
    return {
        "id": ticket.id,
        "student_id": ticket.student_id,
        "issue": ticket.issue,
        "description": ticket.description,
        "location": ticket.location,
        "status": ticket.status,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.scalar(select(Announcement.id).limit(1)) is None:
            db.add_all([
                Announcement(title="Welcome to Campus Care", message="Use this portal to report college facility and IT issues."),
                Announcement(title="API learning activity", message="Try GET /api/announcements without logging in."),
                Announcement(title="Lab reminder", message="Please mention the lab number when reporting a computer issue."),
            ])
            db.commit()

@app.get("/", include_in_schema=False)
def home():
    return FileResponse("static/index.html")

@app.get("/health")
def health():
    return {"status": "ok", "service": "Campus Care API"}

@app.post("/api/auth/signup", status_code=201)
def signup(data: SignupIn, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == data.email.lower()))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(name=data.name.strip(), email=data.email.lower(), password_hash=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user)
    return {"message": "Account created successfully", "access_token": token, "token_type": "bearer",
            "user": {"id": user.id, "name": user.name, "email": user.email}}

@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return {"message": "Login successful", "access_token": create_access_token(user), "token_type": "bearer",
            "user": {"id": user.id, "name": user.name, "email": user.email}}

@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "name": user.name, "email": user.email}

@app.get("/api/announcements")
def announcements(db: Session = Depends(get_db)):
    rows = db.scalars(select(Announcement).order_by(Announcement.id.desc())).all()
    return [{"id": a.id, "title": a.title, "message": a.message} for a in rows]

@app.get("/api/tickets")
def list_tickets(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Ticket).where(Ticket.student_id == user.id)
    if status_filter:
        stmt = stmt.where(Ticket.status == status_filter)
    rows = db.scalars(stmt.order_by(Ticket.id.desc()).limit(limit)).all()
    return [ticket_dict(t) for t in rows]

@app.post("/api/tickets", status_code=201)
def create_ticket(data: TicketIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ticket = Ticket(student_id=user.id, issue=data.issue, description=data.description, location=data.location)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return {"message": "Complaint submitted successfully", "ticket": ticket_dict(ticket)}

@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket or ticket.student_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found for this student.")
    return ticket_dict(ticket)

@app.put("/api/tickets/{ticket_id}")
def replace_ticket(ticket_id: int, data: TicketPut, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket or ticket.student_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found for this student.")
    ticket.issue, ticket.description, ticket.location = data.issue, data.description, data.location
    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return {"message": "Ticket details replaced", "ticket": ticket_dict(ticket)}

@app.patch("/api/tickets/{ticket_id}/status")
def update_ticket_status(ticket_id: int, data: TicketPatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket or ticket.student_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found for this student.")
    ticket.status = data.status
    ticket.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return {"message": "Ticket status updated", "ticket": ticket_dict(ticket)}

@app.delete("/api/tickets/{ticket_id}")
def delete_ticket(ticket_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if not ticket or ticket.student_id != user.id:
        raise HTTPException(status_code=404, detail="Ticket not found for this student.")
    db.delete(ticket)
    db.commit()
    return {"message": f"Ticket {ticket_id} deleted successfully"}

@app.get("/api/integration/tickets")
def integration_tickets(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    if not x_api_key or x_api_key != INTEGRATION_API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid API key.")
    rows = db.scalars(select(Ticket).order_by(Ticket.id.desc()).limit(100)).all()
    return [ticket_dict(t) for t in rows]
