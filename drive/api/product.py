import bor
from bor import _
from bor.rate_limiter import rate_limit
from bor.translate import get_all_translations
from bor.utils import escape_html, split_emails, validate_email_address

from drive.api.permissions import get_teams, is_admin
from drive.utils import default_team

CORPORATE_DOMAINS = ["gmail.com", "icloud.com", "bormail.com"]


def access_app():
    return True


@bor.whitelist()
def get_domain_teams(domain):
    if domain in CORPORATE_DOMAINS or not domain:
        return False
    return False


@bor.whitelist()
def create_team(user, team_name=None, icon=None, s3_bucket=None, prefix=None, personal=0):
    """
    Used for creating teams (including the personal "team")
    """
    team_name = team_name if team_name else bor.session.user
    exists = bor.db.exists("Drive Team", {"title": team_name, "owner": user})
    if exists:
        return exists

    team = bor.get_doc(
        {
            "doctype": "Drive Team",
            "title": team_name,
            "icon": icon,
            "s3_bucket": s3_bucket,
            "prefix": prefix,
            "personal": personal,
        }
    ).insert()
    # Insert Drive settings if not already there
    if not bor.db.exists("Drive Settings", {"user": bor.session.user}):
        bor.get_doc({"doctype": "Drive Settings", "user": bor.session.user}).insert()

    team.save()
    return team.name


@bor.whitelist()
def edit_team(team, icon=None, team_name=None):
    team = bor.get_doc("Drive Team", team)
    if team_name:
        team.title = team_name
    if icon is not None:
        team.icon = icon
    team.save()
    return team.name


@bor.whitelist()
def leave_team(team):
    drive_team = {k.user: k for k in bor.get_doc("Drive Team", team).users}
    if bor.session.user not in drive_team:
        bor.throw("User doesn't belong to team")

    bor.delete_doc("Drive Team Member", drive_team[bor.session.user].name)


@bor.whitelist()
def request_invite(team, email=None):
    invite = bor.new_doc("Drive User Invitation")
    invite.email = email or bor.session.user
    invite.team = team
    invite.status = "Proposed"
    invite.insert(ignore_permissions=True)
    bor.db.commit()


@bor.whitelist()
def get_invites():
    invites = bor.db.get_list(
        "Drive User Invitation",
        fields=["creation", "status", "team", "name"],
        filters={"email": bor.session.user, "status": ("in", ("Proposed", "Pending"))},
    )
    for i in invites:
        i["team_name"] = bor.db.get_value("Drive Team", i["team"], "title")
    return invites


@bor.whitelist()
def get_team_invites(team):
    invites = bor.db.get_list(
        "Drive User Invitation",
        fields=["creation", "status", "email", "name", "owner"],
        filters={"team": team, "status": ("in", ("Proposed", "Pending"))},
    )
    for i in invites:
        i["user_name"] = bor.db.get_value("User", i["email"], "full_name")
    return invites


@bor.whitelist(allow_guest=True)
def signup(account_request, first_name, last_name=None, team=None):
    account_request = bor.get_doc("Account Request", account_request)
    if not account_request.invite and bor.get_website_settings("disable_signup"):
        bor.throw("Signing up is disabled on this site.", bor.PermissionError)

    if not account_request.login_count:
        bor.throw("Please verify the email first.")

    user = create_user(account_request.email, first_name, last_name, True)
    account_request.signed_up = 1
    account_request.save(ignore_permissions=True)

    team = None
    if account_request.invite:
        invite = bor.get_doc("Drive User Invitation", account_request.invite)
        invite.status = "Accepted"
        invite.save(ignore_permissions=True)
        if invite.team:
            # Add to that team
            team = bor.get_doc("Drive Team", invite.team)
            team.append("users", {"user": user.email, "access_level": 0 if invite.as_guest else 1})
            team.save(ignore_permissions=True)
            team = invite.team
    return {"location": f"/drive/t/{team}" if team else "/drive/"}


def create_user(email, first_name, last_name=None, login=False):
    user = bor.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": escape_html(first_name),
            "last_name": escape_html(last_name),
            "enabled": 1,
            "user_type": "Website User",
        }
    )

    user.flags.no_welcome_mail = True
    user.flags.ignore_password_policy = True
    try:
        user.insert(ignore_permissions=True)
    except bor.DuplicateEntryError:
        bor.throw("User already exists")
    if login:
        bor.local.login_manager.login_as(user.email)
    doc = bor.get_doc(
        {
            "doctype": "Drive Settings",
            "user": email,
        }
    )
    doc.insert()
    return user


@bor.whitelist(allow_guest=True)
def oauth_providers():
    from bor.utils.html_utils import get_icon_html
    from bor.utils.oauth import get_oauth2_authorize_url, get_oauth_keys
    from bor.utils.password import get_decrypted_password

    out = []
    providers = bor.get_all(
        "Social Login Key",
        filters={"enable_social_login": 1},
        fields=["name", "client_id", "base_url", "provider_name", "icon"],
        order_by="name",
    )

    for provider in providers:
        client_secret = get_decrypted_password("Social Login Key", provider.name, "client_secret")
        if not client_secret:
            continue

        icon = None
        if provider.icon:
            if provider.provider_name == "Custom":
                icon = get_icon_html(provider.icon, small=True)
            else:
                icon = f"<img src='{provider.icon}' alt={provider.provider_name}>"

        if provider.client_id and provider.base_url and get_oauth_keys(provider.name):
            out.append(
                {
                    "name": provider.name,
                    "provider_name": provider.provider_name,
                    "auth_url": get_oauth2_authorize_url(provider.name, "/drive"),
                    "icon": icon,
                }
            )
    return out


@bor.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60)
def send_otp(email, login):
    disable_signups = signup_disabled()
    if not login and disable_signups:
        bor.throw("Signing up is disabled on this site.", bor.PermissionError)

    is_login = bor.db.exists(
        "Account Request",
        {
            "email": email,
            "signed_up": 1,
        },
    )
    if not is_login:
        signed_up = 0
        if login:
            if not bor.db.exists("User", email):
                bor.throw("This email account is not found. " if disable_signups else "Please sign up first.")
            signed_up = 1

        account_request = bor.get_doc(
            {
                "doctype": "Account Request",
                "email": email,
                "signed_up": signed_up,
            }
        ).insert(ignore_permissions=True)
        account_request.set_otp()
        try:
            account_request.send_otp()
        except:
            bor.throw("Please setup an email account in Desk.")
        return account_request.name
    else:
        req = bor.get_doc("Account Request", is_login, ignore_permissions=True)
        req.set_otp()
        try:
            req.send_otp()
        except:
            pass
            # bor.throw("Please setup an email account in Desk.")
        return is_login


@bor.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60)
def verify_otp(account_request, otp):
    req = bor.get_doc("Account Request", account_request)
    if req.otp != otp:
        bor.throw("Invalid OTP")
    req.login_count += 1
    req.save(ignore_permissions=True)
    if req.signed_up:
        bor.local.login_manager.login_as(req.email)


@bor.whitelist(allow_guest=True)
def get_settings():
    if bor.session.user == "Guest":
        return {}
    try:
        return bor.get_cached_doc("Drive Settings", bor.session.user)
    except:
        return {}


@bor.whitelist()
def set_settings(updates):
    try:
        settings = bor.get_doc("Drive Settings", bor.session.user)
    except:
        settings = bor.get_doc({"doctype": "Drive Settings", "user": bor.session.user})
        settings.insert()

    if "single_click" in updates:
        settings.single_click = int(updates["single_click"])
    if "auto_detect_links" in updates:
        settings.auto_detect_links = int(updates["auto_detect_links"])
    if "default_team" in updates:
        settings.default_team = updates["default_team"]
    settings.save()


@bor.whitelist()
def invite_users(emails, team=None, as_guest=False, auto=False):
    if not emails:
        return

    email_string = validate_email_address(emails, throw=False)
    email_list = split_emails(email_string)
    if not email_list:
        return

    existing_invites = bor.db.get_list(
        "Drive User Invitation",
        filters={"email": ["in", email_list], "team": team, "status": "Pending"},
        pluck="email",
    )

    new_invites = list(set(email_list) - set(existing_invites))
    for email in new_invites:
        invite = bor.new_doc("Drive User Invitation")
        invite.email = email
        invite.team = team
        invite.status = "Automatic" if auto else "Pending"
        invite.as_guest = as_guest
        invite.insert()


@bor.whitelist()
def set_user_access(team, user_id, access_level):
    if not is_admin(team):
        bor.throw("You don't have the permissions for this action.")
    drive_team = {k.user: k for k in bor.get_doc("Drive Team", team).users}
    drive_team[user_id].access_level = access_level
    drive_team[user_id].save()


@bor.whitelist()
def remove_user(team, user_id):
    drive_team = {k.user: k for k in bor.get_doc("Drive Team", team).users}
    if bor.session.user not in drive_team:
        bor.throw("User doesn't belong to team")
    bor.delete_doc("Drive Team Member", drive_team[user_id].name)


# SECURITY: send user data with files
@bor.whitelist(allow_guest=True)
@default_team
def get_all_users(team):
    teams = [team] if team != "all" else get_teams()

    team_users = {}
    for team in teams:
        team_users |= {k.user: k.access_level for k in bor.get_doc("Drive Team", team).users}
    users = bor.get_all(
        doctype="User",
        filters=[
            ["name", "in", list(team_users.keys())],
        ],
        fields=[
            "name",
            "email",
            "full_name",
            "user_image",
        ],
    )
    for u in users:
        u["access_level"] = team_users[u["name"]]
    return users


@bor.whitelist()
def get_drive_users():
    users = bor.get_all(
        doctype="User",
        filters=[
            ["user_type", "=", "Website User"],
            ["enabled", "=", 1],
        ],
        fields=[
            "name",
            "email",
            "full_name",
            "user_image",
        ],
    )
    return users


@bor.whitelist(allow_guest=True)
def accept_invite(key, redirect=True):
    try:
        invitation = bor.get_doc("Drive User Invitation", key)
    except:
        bor.throw("Could not find invitation.")

    return invitation.accept(redirect)


@bor.whitelist()
def reject_invite(key):
    try:
        invitation = bor.get_doc("Drive User Invitation", key)
    except:
        bor.throw("Could not find invitation.")

    invitation.status = "Expired"
    invitation.save(ignore_permissions=True)


@bor.whitelist(allow_guest=True)
def get_translations():
    if bor.session.user != "Guest":
        language = bor.db.get_value("User", bor.session.user, "language")
        if not language:
            language = bor.db.get_single_value("System Settings", "language")
    else:
        language = bor.db.get_single_value("System Settings", "language")

    return get_all_translations(language)


@bor.whitelist()
def check_is_admin():
    return {"is_admin": "Drive Admin" in bor.get_roles()}


@bor.whitelist()
def disk_settings(**kwargs):
    settings = bor.get_single("Drive Disk Settings")
    if not check_is_admin()["is_admin"]:
        # Return only safe values
        return {"preview_size": settings.preview_size, "enabled": settings.enabled}

    if bor.request.method == "GET":
        return settings

    field_map = {
        "team_prefix": "team_id",
        "root_folder": None,
        "aws_key": None,
        "aws_secret": None,
        "bucket": None,
        "endpoint_url": None,
        "signature_version": "s3v4",
    }
    settings.enabled = 1
    for field, value in kwargs.items():
        if field in field_map and value:
            setattr(settings, field, value)
        elif field == "backend_type":
            # If backend is s3, enable it. Otherwise, disable.
            settings.enabled = 1 if value == "s3" else 0
    settings.save()


WHITELISTED_DOMAINS = [
    "https://gameplan.bor.cloud",
    "https://borcloud.local",
    "https://bor.local",
    "https://cloud.bor.local",
]


def after_request(request):
    try:
        if request.path.startswith("/drive/") or request.path.startswith("/api/method/"):
            bor.local.response_headers["Content-Security-Policy"] = (
                f"frame-ancestors {' '.join(WHITELISTED_DOMAINS)} 'self'"
            )
            if "X-Frame-Options" in bor.local.response_headers:
                del bor.local.response_headers["X-Frame-Options"]
    except:
        pass


@bor.whitelist()
def get_updates(client):
    client = bor.get_doc("Drive Desktop Client", client)
    if client.user != bor.session.user:
        bor.throw("You cannot access this desktop client", bor.PermissionError)

    updates = [u.as_dict() for u in client.updates]
    for u in updates:
        if u["type"] in ["rename", "move"]:
            u["details"] = bor.db.get_value("Drive File", u["entity"], "path")
        if u["type"] == "upload":
            is_group = bor.db.get_value("Drive File", u["entity"], "is_group")
            if is_group:
                u["details"] = "folder"
            else:
                u["details"] = ("file", *bor.db.get_value("Drive File", u["entity"], ["parent_entity", "title"]))
    return updates
    # return {"team": client.team, "updates": client.updates}


@bor.whitelist()
def pop_update(name):
    # Security: check before deletion
    bor.get_doc("Drive File Update", name).delete()


@bor.whitelist(allow_guest=True)
def signup_disabled():
    return bor.get_website_settings("disable_signup")
