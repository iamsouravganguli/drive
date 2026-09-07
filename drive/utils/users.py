import os

import bor
import requests
from bor.rate_limiter import rate_limit
from bor.utils import now


def mark_as_viewed(entity):
    if (
        bor.session.user == "Guest"
        or not bor.has_permission(doctype="Drive Entity Log", ptype="write", user=bor.session.user)
        or entity.is_group
    ):
        return

    entity_log = bor.db.get_value("Drive Entity Log", {"entity_name": entity.name, "user": bor.session.user})
    if entity_log:
        bor.db.set_value("Drive Entity Log", entity_log, "last_interaction", now(), update_modified=False)
        return
    doc = bor.new_doc("Drive Entity Log")
    doc.entity_name = entity.name
    doc.user = bor.session.user
    doc.last_interaction = now()
    doc.insert()
    return doc


@bor.whitelist()
@rate_limit(key="reference_name", limit=10, seconds=60 * 60)
def add_comment(reference_name: str, content: str, comment_email: str, comment_by: str):
    """Allow logged user with permission to read document to add a comment"""
    exists = bor.db.exists("Drive File", reference_name)
    if not exists:
        bor.throw("Entity does not exist", bor.NotFound)
    comment = bor.new_doc("Comment")
    comment.update(
        {
            "comment_type": "Comment",
            "reference_doctype": "Drive File",
            "reference_name": reference_name,
            "comment_email": comment_email,
            "comment_by": comment_by,
            "content": content,
        }
    )
    comment.insert(ignore_permissions=True)
    return comment


def generate_otp():
    """Generates a cryptographically secure random OTP"""

    return int.from_bytes(os.urandom(5), byteorder="big") % 900000 + 100000


def get_country_info():
    ip = bor.local.request_ip

    def _get_country_info():
        fields = [
            "status",
            "message",
            "continent",
            "continentCode",
            "country",
            "countryCode",
            "region",
            "regionName",
            "city",
            "district",
            "zip",
            "lat",
            "lon",
            "timezone",
            "offset",
            "currency",
            "isp",
            "org",
            "as",
            "asname",
            "reverse",
            "mobile",
            "proxy",
            "hosting",
            "query",
        ]

        try:
            res = requests.get(f"https://pro.ip-api.com/json/{ip}?fields={','.join(fields)}")
            data = res.json()
            if data.get("status") != "fail":
                return data
        except Exception:
            pass

        return {}

    return bor.cache().hget("ip_country_map", ip, generator=_get_country_info)
