"""
Temporary in-memory storage for Groups.
Resets on server restart — same limitation as users_db, will move
to PostgreSQL together in the database phase.
"""

groups_db: dict[str, dict] = {}              # keyed by group id
group_members_db: dict[str, list[str]] = {}  # group_id -> list of user emails