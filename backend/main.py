from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from passlib.context import CryptContext
from bson import ObjectId

from database import get_database
from models import NewsArticleCreate, NewsArticleResponse, Token, TokenData, UserInDB
from auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    check_admin,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
import os
from fastapi.security import APIKeyHeader
from datetime import timedelta

app = FastAPI(title="GlobalPulse24 Backend API", version="1.0.0")

# CORS Configuration
# Allow frontend URL from environment variable, fallback to wildcard
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security for new Admin Routes using ADMIN_PASSWORD
admin_api_key_header = APIKeyHeader(name="X-Admin-Token", auto_error=False)

def verify_admin_password(api_key_header: str = Depends(admin_api_key_header)):
    admin_password = os.getenv("ADMIN_PASSWORD", "supersecret123")
    if api_key_header != admin_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Admin Password"
        )
    return True

# Startup event to ensure admin user exists for testing
@app.on_event("startup")
async def startup_db_client():
    db = get_database()
    # Check if admin user exists
    admin_user = await db["users"].find_one({"username": "yash"})
    if not admin_user:
        hashed_pw = get_password_hash("admin123")  # Default password for testing
        await db["users"].insert_one({
            "username": "yash",
            "hashed_password": hashed_pw,
            "role": "admin"
        })
        print("Created default admin user: yash / admin123")

# Authentication Routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_database)):
    user = await db["users"].find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user.get("role", "user")},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# News Routes
@app.post("/news/submit", response_model=NewsArticleResponse, status_code=status.HTTP_201_CREATED)
async def submit_news(article: NewsArticleCreate, db = Depends(get_database)):
    """Publisher submits an article. Status defaults to 'pending'."""
    article_dict = article.model_dump()
    article_dict["status"] = "pending"
    article_dict["timestamp"] = article_dict.get("timestamp") # Will be set by model
    
    # Motor doesn't validate strictly, so we prepare the document
    from models import NewsArticleDB
    db_article = NewsArticleDB(**article_dict)
    
    doc = db_article.model_dump()
    result = await db["articles"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return doc

@app.get("/news/live", response_model=List[NewsArticleResponse])
async def get_live_news(db = Depends(get_database)):
    """Fetch only 'approved' news for the homepage."""
    articles = []
    cursor = db["articles"].find({"status": "approved"}).sort("timestamp", -1)
    async for document in cursor:
        document["id"] = str(document["_id"])
        articles.append(document)
    return articles

@app.get("/admin/pending", response_model=List[NewsArticleResponse])
async def get_pending_news(
    is_admin: bool = Depends(verify_admin_password),
    db = Depends(get_database)
):
    """Admin route to fetch all 'pending' news for approval."""
    articles = []
    cursor = db["articles"].find({"status": "pending"}).sort("timestamp", -1)
    async for document in cursor:
        document["id"] = str(document["_id"])
        articles.append(document)
    return articles

@app.put("/admin/approve/{id}", response_model=NewsArticleResponse)
async def approve_news(
    id: str, 
    is_admin: bool = Depends(verify_admin_password), 
    db = Depends(get_database)
):
    """Admin route to approve an article, changing status from 'pending' to 'published'."""
    try:
        obj_id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Article ID")

    result = await db["articles"].update_one(
        {"_id": obj_id},
        {"$set": {"status": "published"}}
    )
    
    if result.modified_count == 0:
        # Check if it even exists
        existing = await db["articles"].find_one({"_id": obj_id})
        if not existing:
             raise HTTPException(status_code=404, detail="Article not found")
        # If it exists but wasn't modified, maybe it was already published
        
    updated_article = await db["articles"].find_one({"_id": obj_id})
    updated_article["id"] = str(updated_article["_id"])
    return updated_article

@app.get("/news/earnings")
async def get_publisher_earnings(current_user: TokenData = Depends(get_current_user), db = Depends(get_database)):
    """Publishers can see their own earnings based on their articles."""
    articles = await db["articles"].count_documents({"author": current_user.username, "status": "approved"})
    # Mock calculation: $50 per approved article
    revenue = articles * 50
    return {"total_revenue": revenue, "approved_articles": articles, "pending_payments": revenue}

@app.get("/admin/payouts")
async def get_all_payouts(current_admin: TokenData = Depends(check_admin), db = Depends(get_database)):
    """Admin can see all payouts across all publishers."""
    pipeline = [
        {"$match": {"status": "approved"}},
        {"$group": {"_id": "$author", "count": {"$sum": 1}}}
    ]
    cursor = db["articles"].aggregate(pipeline)
    payouts = []
    async for doc in cursor:
        payouts.append({
            "publisher": doc["_id"],
            "approved_articles": doc["count"],
            "earnings": doc["count"] * 50
        })
    return {"payouts": payouts}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
