from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os


SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30


pwd_context = CryptContext(schemes=['bcrypt'], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)


engine = None
SessionLocal = None


def init_auth(app: FastAPI, database_url: str = "sqlite:///./auth.db"):

    global engine, SessionLocal

    engine = create_engine(
        database_url,
        connect_args={
            "check_same_thread": False} if "sqlite" in database_url else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    add_auth_routes(app)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return email
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


def create_user(db: Session, user_data: dict):
    if get_user_by_email(db, user_data["email"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user_data["password"])
    db_user = User(
        email=user_data["email"],
        username=user_data.get("username"),
        full_name=user_data.get("full_name"),
        hashed_password=hashed_password,
        role=user_data.get("role", "user"),
        is_active=user_data.get("is_active", True),
        is_verified=user_data.get("is_verified", False)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = verify_token(token)
    user = get_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_manager(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager access required"
        )
    return current_user


def require_admin_or_manager(current_user: User = Depends(get_current_active_user)):
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Manager access required"
        )
    return current_user


def add_auth_routes(app: FastAPI):

    class UserCreate(BaseModel):
        email: EmailStr
        username: Optional[str] = None
        full_name: Optional[str] = None
        password: str

    class UserResponse(BaseModel):
        id: int
        email: str
        username: Optional[str] = None
        full_name: Optional[str] = None
        role: str
        is_active: bool
        is_verified: bool

        class Config:
            from_attributes = True

    class Token(BaseModel):
        access_token: str
        token_type: str

    class UpdateUserRole(BaseModel):
        user_id: int
        new_role: str

    @app.post("/auth/register", response_model=UserResponse, tags=["Authentication"])
    def register(user: UserCreate, db: Session = Depends(get_db)):
        user_data = user.dict()
        user_data["role"] = "user"
        return create_user(db, user_data)

    @app.post("/auth/token", response_model=Token, tags=["Authentication"])
    def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )

        access_token_expires = timedelta(minutes=TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

    @app.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
    def get_me(current_user: User = Depends(get_current_active_user)):
        return current_user

    @app.get("/auth/users", response_model=List[UserResponse], tags=["Authentication"])
    def get_users(admin_user: User = Depends(require_admin), db: Session = Depends(get_db)):
        return db.query(User).all()

    @app.post("/auth/admin/assign-role", tags=["Authentication"])
    def assign_user_role(
        role_update: UpdateUserRole,
        admin_user: User = Depends(require_admin),
        db: Session = Depends(get_db)
    ):

        user = db.query(User).filter(User.id == role_update.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        valid_roles = ["user", "manager", "admin"]
        if role_update.new_role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )

        user.role = role_update.new_role
        db.commit()

        return {
            "message": f"User {user.email} role updated to {role_update.new_role}",
            "user_id": user.id,
            "new_role": user.role
        }

    @app.get("/auth/admin/users-by-role/{role}", tags=["Authentication"])
    def get_users_by_role(
        role: str,
        admin_user: User = Depends(require_admin),
        db: Session = Depends(get_db)
    ):

        users = db.query(User).filter(User.role == role).all()
        return {
            "role": role,
            "count": len(users),
            "users": [{"id": u.id, "email": u.email, "full_name": u.full_name} for u in users]
        }
