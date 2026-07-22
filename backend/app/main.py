"""
DIOS Backend — entry point.
Every new domain (mfa, oauth, billing, video...) gets built as
its own router file, then added here with one line.
"""

from fastapi import FastAPI

from app.routers import auth, password,  mfa, oauth, tokens, profile, organizations, api_keys, service_accounts, roles, permissions, role_assignments, policies, access, org_authorization, teams, resources, user_management, devices, security, admin_users, admin_org_roles, admin_platform, admin_system, admin_security, admin_backup, authz_audit, groups, workspaces, activity, sessions, notifications, email, sms_push, inapp, preferences, notifications_admin, membership, departments, audit_domain, monitoring,monitoring_metrics,monitoring_logs,monitoring_alerts , monitoring_tracing  ,monitoring_admin , billing_customers ,billing_subscriptions,billing_payments,billing_invoices

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
app.include_router(permissions.router)
app.include_router(role_assignments.router)
app.include_router(policies.router)
app.include_router(access.router)
app.include_router(org_authorization.router)
app.include_router(teams.router)
app.include_router(resources.router)
app.include_router(user_management.router)
app.include_router(devices.router)
app.include_router(security.router)
app.include_router(admin_users.router)
app.include_router(admin_org_roles.router)
app.include_router(admin_platform.router)
app.include_router(admin_system.router)
app.include_router(admin_security.router)
app.include_router(admin_backup.router)
app.include_router(authz_audit.router)
app.include_router(groups.router)
app.include_router(workspaces.router)
app.include_router(activity.router)
app.include_router(sessions.router)
app.include_router(notifications.router)
app.include_router(email.router)
app.include_router(sms_push.router)
app.include_router(inapp.router)
app.include_router(preferences.router)
app.include_router(notifications_admin.router)
app.include_router(membership.router)
app.include_router(departments.router)
app.include_router(audit_domain.router)
app.include_router(monitoring.router)
app.include_router(monitoring_metrics.router)
app.include_router(monitoring_logs.router)
app.include_router(monitoring_alerts.router)
app.include_router(monitoring_tracing.router)
app.include_router(monitoring_admin.router)
app.include_router(billing_customers.router)
app.include_router(billing_subscriptions.router)
app.include_router(billing_payments.router)
app.include_router(billing_invoices.router)



@app.get("/")
def root():
    return {"message": "DIOS API is running"}