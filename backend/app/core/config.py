"""
Central configuration.
Values are hardcoded for now, for local development only.
Later we'll move these into a .env file so secrets never get
committed to GitHub.
"""

SECRET_KEY = "dev-secret-change-this-later"  # TODO: move to .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7