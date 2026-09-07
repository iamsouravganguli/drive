from datetime import datetime, timedelta

import bor
from bor.rate_limiter import rate_limit

from drive.utils import strip_comment_spans

from .permissions import user_has_permission
import mimemapper


@bor.whitelist(allow_guest=True)
def save_doc_comment(entity_name, doc_name, content):
    if not user_has_permission(entity_name, "comment"):
        raise bor.PermissionError("You do not have permission to comment on this file")


@bor.whitelist(allow_guest=True)
@rate_limit(key="create_comment", limit=10, seconds=1)
def create_comment(entity_name, name, content, is_reply, parent_name=None):
    doc = bor.get_doc("Drive File", entity_name)
    parent = bor.get_doc("Drive Comment", parent_name) if is_reply else doc

    if not user_has_permission(doc, "comment"):
        bor.throw("You don't have comment access")

    comment = bor.get_doc(
        {
            "doctype": "Drive Comment",
            "name": name,
            "content": content,
        }
    )
    parent.append("replies" if is_reply else "comments", comment)
    parent.save(ignore_permissions=True)
    comment.insert(ignore_permissions=True)
    return comment.name


@bor.whitelist()
def edit_comment(name, content):
    comment = bor.get_doc("Drive Comment", name)
    if comment.owner != bor.session.user:
        bor.throw("You can't edit comments you don't own.")
    comment.content = content
    comment.save()
    return name


@bor.whitelist()
def delete_comment(name, entire=True):
    comment = bor.get_doc("Drive Comment", name)
    if comment.owner != bor.session.user and comment.owner != "Guest":
        bor.throw("You can't edit comments you don't own.")
    if entire:
        for r in comment.replies:
            r.delete()
    comment.delete()


@bor.whitelist()
def resolve_comment(name, value):
    comment = bor.get_doc("Drive Comment", name)
    comment.resolved = value
    comment.save()


@bor.whitelist(allow_guest=True)
def get_wiki_link(title, team):
    title = title.strip("/")
    possible_titles = [title, title + ".md", title + ".txt"]
    names = (bor.get_value("Drive File", {"title": k, "team": team, "is_group": 0}, "name") for k in possible_titles)
    try:
        name = next(k for k in names if k)
    except StopIteration:
        bor.throw("Cannot get this wikilink in this team.", bor.NotFound)

    bor.local.response["type"] = "redirect"
    bor.local.response["location"] = "/drive/f/" + name
    return title


@bor.whitelist()
def create_version(doc, snapshot, duration=None, manual=0, title=""):
    if not manual:
        versions = bor.get_all(
            "Drive Doc Version",
            filters={"parent": doc, "manual": 0},
            fields=["*"],
            order_by="idx desc",
            limit_page_length=1,
        )
        if versions:
            title = bor.get_doc("Drive Doc Version", versions[0].name).title
            prev_time = datetime.strptime(title, "%Y-%m-%d %H:%M")
            now_time = bor.utils.now_datetime()
            diff = now_time - prev_time
            if duration is not None and diff < timedelta(minutes=duration):
                return False
            title = datetime.strftime(now_time, "%Y-%m-%d %H:%M")
        else:
            title = datetime.strftime(bor.utils.now_datetime(), "%Y-%m-%d %H:%M")

    doc = bor.get_doc("Drive Document", doc)
    doc.append(
        "versions",
        {
            "snapshot": snapshot,
            "manual": int(manual),
            "title": title,
        },
    )
    try:
        doc.save()
    except bor.QueryDeadlockError:
        doc = bor.get_doc("Drive Document", doc.name)
        doc.append(
            "versions",
            {
                "snapshot": snapshot,
                "manual": int(manual),
                "title": title,
            },
        )
        doc.save()
    return doc.versions


# To be moved to mimemapper
QUICK_MAP = {
    "video/quicktime": "mov",
    "image/gif": "gif",
}


@bor.whitelist()
def get_extension(entity_name):
    mime_type = bor.get_value("Drive File", entity_name, "mime_type")
    try:
        return mimemapper.get_extension(mime_type)
    except:
        return QUICK_MAP.get(mime_type, "")


@bor.whitelist()
def create_blog(entity_name, html, attachments=None):
    """
    If the blog app is installed, creates a blog
    """
    file = bor.get_doc("Drive File", entity_name)
    blogger = bor.db.exists("Blogger", {"user": bor.session.user})
    if not blogger:
        bor.throw("Please create a Blogger for your user first.")

    if not bor.db.exists("Blog Category", {"name": "writer-export"}):
        category = bor.get_doc({"doctype": "Blog Category", "title": "Writer Export"})
        category.insert()
        print("insrted", category, category.name)
    else:
        category = bor.get_doc("Blog Category", "writer-export")

    blog = bor.get_doc(
        {
            "doctype": "Blog Post",
            "title": file.title,
            "content_type": "HTML",
            "blog_category": category.name,
            "blogger": blogger,
            "content_html": html,
        }
    )
    blog.insert()
    return blog.name
