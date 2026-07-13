"""
DIOS Backend — entry point.
Every new domain (mfa, oauth, billing, video...) gets built as
its own router file, then added here with one line.
"""

from fastapi import FastAPI

from app.routers import auth, users, password, mfa,oauth

app = FastAPI(title="DIOS API", version="0.1.0")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(password.router)
app.include_router(mfa.router)
app.include_router(oauth.router)
# Coming later:
# app.include_router(oauth.router)


@app.get("/")
def root():
    return {"message": "DIOS API is running"}