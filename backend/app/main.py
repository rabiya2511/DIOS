"""
DIOS Backend — entry point.
Every new domain (mfa, oauth, billing, video...) gets built as
its own router file, then added here with one line.
"""

from fastapi import FastAPI

from app.routers import auth, password, mfa, oauth, tokens, profile, organizations, api_keys, service_accounts, roles, devices, security

app = FastAPI(title="DIOS API", version="0.1.0")

app.include_router(auth.router)
app.include_router(password.router)
app.include_router(mfa.router)
app.include_router(oauth.router)
app.include_router(tokens.router)
app.include_router(profile.router)
app.include_router(organizations.router)
app.include_router(api_keys.router)
app.include_router(service_accounts.router)
app.include_router(roles.router)
app.include_router(devices.router)
app.include_router(security.router)


@app.get("/")
def root():
    return {"message": "DIOS API is running"}