from __future__ import unicode_literals

import bor

from drive.api.permissions import get_user_access

no_cache = 1

TITLES = {"login": "Login", "signup": "Create an Account"}


def get_context():
    csrf_token = bor.sessions.get_csrf_token()
    bor.db.commit()
    context = bor._dict()
    context.boot = get_boot()
    context.boot.csrf_token = csrf_token
    context.csrf_token = csrf_token
    context.site_name = bor.local.site

    context.title = "Bor Drive"
    context.description = "Visit Drive online."

    if not bor.form_dict.app_path:
        return context

    # Parsing
    parts = bor.form_dict.app_path.split("/")
    if len(parts) >= 3:
        context.description = "Open this online."
        # Ideally add thumbnail, but that might break if there's no thumbnail
        try:
            [title, owner, is_group] = bor.get_cached_value("Drive File", parts[1], ["title", "owner", "is_group"])
            context.title = "Folder - " + title if is_group else title
            context.description = "Owned by " + bor.get_cached_value("User", owner, "full_name")
        except:
            pass

    elif parts[0] in TITLES:
        context.title = TITLES[parts[0]]
        context.description = ""
    return context


@bor.whitelist(methods=["POST"])
def get_context_for_dev():
    if not bor.conf.developer_mode:
        bor.throw("This method is only meant for developer mode")
    return get_boot()


def get_boot():
    return bor._dict(
        {
            "bor_version": bor.__version__,
            "default_route": get_default_route(),
            "site_name": bor.local.site,
            "read_only_mode": bor.flags.read_only,
        }
    )


def get_default_route():
    return "/drive"
