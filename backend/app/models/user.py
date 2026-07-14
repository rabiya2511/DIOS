"""
Temporary in-memory "database".
Resets every time the server restarts — that's expected for now.
Once PostgreSQL is set up, this file gets replaced with real
database models, and the rest of the app barely has to change.
"""

users_db: dict[str, dict] = {}                    # keyed by email
refresh_tokens_db: dict[str, str] = {}             # refresh_token -> email
password_reset_tokens_db: dict[str, str] = {}      # reset_token -> email
mfa_secrets_db: dict[str, dict] = {}               # email -> {secret, confirmed}
mfa_backup_codes_db: dict[str, list[str]] = {} 
email_verification_tokens_db: dict[str, str] = {}   # token -> email
invites_db: dict[str, dict] = {}                     # invite_token -> {"email":..., "organization_id":..., "role":...}
organizations_db: dict[str, dict] = {}               # org_id -> {"name":..., "owner_email":..., "created_at":...}
passwordless_tokens_db: dict[str, str] = {}           # login_token -> email
device_codes_db: dict[str, dict] = {}  
password_history_db: dict[str, list[str]] = {} 
oauth_connections_db: dict[str, dict[str, str]] = {} 
service_accounts_db: dict[str, dict] = {}  
roles_db: dict[str, dict] = {}   # id -> {id, name, permissions, created_at} # id -> {id, name, owner_email, active, created_at}  # email -> {provider: provider_user_id}   # email -> list of previous hashed passwords               # device_code -> {"user_code":..., "email": None, "approved": False}    # email -> list of unused backup codes
devices_db: dict[str, dict] = {}   # id -> {id, owner_email, name, trusted, active, created_at, last_active_at}
security_events_db: dict[str, list[dict]] = {}    # email -> list of {event, timestamp, detail}
login_history_db: dict[str, list[dict]] = {}       # email -> list of {success, timestamp, ip}
audit_logs_db: list[dict] = []                      # global list of {actor_email, action, timestamp}