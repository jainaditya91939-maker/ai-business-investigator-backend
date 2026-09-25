import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

from database import engine


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)


JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "CHANGE_THIS_SECRET_IN_PRODUCTION"
)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7


class SignupRequest(BaseModel):
    name: str
    business_name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def create_access_token(user_id: int, business_id: int):
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "business_id": business_id,
        "exp": expire
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )


@router.post("/signup")
def signup(request: SignupRequest):

    if len(request.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    email = request.email.lower().strip()

    with engine.begin() as connection:

        existing_user = connection.execute(
            text("""
                SELECT id
                FROM users
                WHERE email = :email
            """),
            {
                "email": email
            }
        ).fetchone()

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists"
            )

        business_result = connection.execute(
            text("""
                INSERT INTO businesses (name)
                VALUES (:business_name)
                RETURNING id
            """),
            {
                "business_name": request.business_name.strip()
            }
        )

        business_id = business_result.scalar()

        password_hash = bcrypt.hashpw(
            request.password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        user_result = connection.execute(
            text("""
                INSERT INTO users (
                    business_id,
                    name,
                    email,
                    password_hash
                )
                VALUES (
                    :business_id,
                    :name,
                    :email,
                    :password_hash
                )
                RETURNING id, name, email, business_id
            """),
            {
                "business_id": business_id,
                "name": request.name.strip(),
                "email": email,
                "password_hash": password_hash
            }
        )

        user = user_result.fetchone()

    token = create_access_token(
        user_id=user.id,
        business_id=user.business_id
    )

    return {
        "status": "SUCCESS",
        "message": "Account created successfully",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "business_id": user.business_id
        }
    }


@router.post("/login")
def login(request: LoginRequest):

    email = request.email.lower().strip()

    with engine.connect() as connection:

        user = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    email,
                    password_hash,
                    business_id
                FROM users
                WHERE email = :email
            """),
            {
                "email": email
            }
        ).fetchone()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    password_valid = bcrypt.checkpw(
        request.password.encode("utf-8"),
        user.password_hash.encode("utf-8")
    )

    if not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token(
        user_id=user.id,
        business_id=user.business_id
    )

    return {
        "status": "SUCCESS",
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "business_id": user.business_id
        }
    }


@router.get("/me")
def get_current_user_from_token(token: str):

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )

        user_id = payload.get("sub")
        business_id = payload.get("business_id")

        if not user_id or not business_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Authentication token has expired"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

    with engine.connect() as connection:

        user = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    email,
                    business_id
                FROM users
                WHERE id = :user_id
                  AND business_id = :business_id
            """),
            {
                "user_id": int(user_id),
                "business_id": int(business_id)
            }
        ).fetchone()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return {
        "status": "SUCCESS",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "business_id": user.business_id
        }
    }