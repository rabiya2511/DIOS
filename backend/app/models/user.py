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
permission_overrides_db: dict[str, str] = {}   # permission_key -> overridden description
policies_db: dict = {
    "password_min_length": 8,
    "password_require_uppercase": True,
    "password_require_number": True,
    "session_timeout_minutes": 30,
    "mfa_required_for_admins": False,
}
platform_config_db: dict = {
    "site_name": "DIOS",
    "support_email": "support@dios.example.com",
    "maintenance_mode": False,
}
feature_flags_db: dict = {
    "new_dashboard": False,
    "beta_api_access": False,
    "dark_mode": True,
}
licenses_db: dict = {
    "plan": "Enterprise",
    "seats": 100,
    "seats_used": 1,
    "expires_at": "2027-01-01T00:00:00Z",
}
branding_db: dict = {
    "logo_url": "",
    "primary_color": "#000000",
    "company_name": "DIOS",
}
system_ops_log_db: list[dict] = []   # {operation, timestamp, triggered_by}
backups_db: list[dict] = []   # {id, created_at, triggered_by}
app_logs_db: list[dict] = [
    {"level": "INFO", "message": "Application started", "timestamp": "2026-07-15T00:00:00Z"},
]
alerts_db: list[dict] = [
    {"id": "alert-1", "severity": "warning", "message": "High memory usage detected", "active": True},
]
admin_settings_db: dict = {
    "backup_frequency_hours": 24,
    "log_retention_days": 30,
    "alert_email": "alerts@dios.example.com",
}
resource_owners_db: dict[str, str] = {}                    # resource_id -> owner_email
resource_shares_db: dict[str, list[dict]] = {}              # resource_id -> [{id, email, permission}]
resource_locks_db: dict[str, bool] = {}    
service_account_roles_db: dict[str, list[str]] = {}         # account_id -> [role names]
service_account_permissions_db: dict[str, list[str]] = {}   # account_id -> [permission keys]
service_account_secrets_db: dict[str, str] = {}              # account_id -> current secret
authz_audit_db: list[dict] = []       # {id, actor_email, action, resource_type, resource_id, timestamp, archived}
authz_violations_db: list[dict] = []  # {id, actor_email, action, reason, timestamp} — populated by access checks later
authz_reviews_db: list[dict] = []     # {id, reviewer_email, note, timestamp}
groups_db: dict[str, dict] = {}                # id -> {id, name, creator_email, created_at}
group_members_db: dict[str, list[str]] = {}    # group_id -> [emails]
groups_db: dict[str, dict] = {}              # keyed by group id
group_members_db: dict[str, list[str]] = {}  # group_id -> list of user emails