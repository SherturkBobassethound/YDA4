"""
Authentication middleware for Supabase JWT tokens
"""
import os
from typing import Optional
from fastapi import HTTPException, Header
from jose import jwt, JWTError
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Extract JWT secret from service key if not provided separately
# The service key is a JWT token itself, we need the actual secret
# For Supabase, you can find this in: Project Settings > API > JWT Secret
if not SUPABASE_JWT_SECRET:
    print("Warning: SUPABASE_JWT_SECRET not found in .env. Please add it for production use.")
    print("You can find it in Supabase Dashboard > Project Settings > API > JWT Secret")


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Verify and decode the JWT token from the Authorization header.
    Returns the user data from the token.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing"
        )

    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme"
            )

        # For development, we'll skip verification if JWT_SECRET is not set
        # In production, you MUST set SUPABASE_JWT_SECRET
        if not SUPABASE_JWT_SECRET:
            # Decode without verification (DEVELOPMENT ONLY)
            payload = jwt.get_unverified_claims(token)
            print("⚠️ WARNING: Running in development mode without JWT verification!")
        else:
            # Verify and decode the token
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}  # Supabase doesn't use aud claim
            )

        # Extract user information
        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: missing user ID"
            )

        return {
            "id": user_id,
            "email": email,
            "payload": payload
        }

    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format"
        )
    except JWTError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )


async def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Optional authentication - returns user if authenticated, None otherwise.
    Useful for endpoints that work with or without authentication.
    """
    if not authorization:
        return None

    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
