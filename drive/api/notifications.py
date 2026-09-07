import bor
from pypika import Order


def get_link(entity):
    type_ = {True: "f", bool(entity.is_group): "d", bool(entity.document): "w"}
    return entity.path if entity.is_link else f"/drive/{type_.get(True)}/{entity.name}/"


@bor.whitelist()
def get_notifications(only_unread):
    """
    Get notifications for current user

    :param only_unread: only get notifications where read is False
    """
    User = bor.qb.DocType("User")
    Notification = bor.qb.DocType("Drive Notification")
    fields = [
        Notification.name,
        Notification.to_user,
        Notification.from_user,
        Notification.read,
        Notification.type,
        Notification.message,
        Notification.entity_type,
        Notification.notif_doctype,
        Notification.notif_doctype_name,
        Notification.creation,
        User.user_image,
        User.full_name,
    ]
    query = (
        bor.qb.from_(Notification)
        .left_join(User)
        .on(Notification.from_user == User.name)
        .select(*fields)
        .orderby(Notification.creation, order=Order.desc)
    )

    if only_unread:
        query = query.where(Notification.read == 0)
    query = query.where(Notification.to_user == bor.session.user)
    result = query.run(as_dict=True)
    return result


@bor.whitelist()
def get_unread_count():
    """
    Return a count of records where user is current user and read is False
    """
    return bor.db.count("Drive Notification", filters={"to_user": bor.session.user, "read": 0})


@bor.whitelist()
def mark_as_read(name=None, all=False):
    """
    Mark notification for current user as read

    :param name: ID of notification record
    :param all: Will mark all unread notifications as read
    """
    if all:
        bor.db.set_value("Drive Notification", {"to_user": bor.session.user, "read": False}, "read", True)
        return
    bor.db.set_value("Drive Notification", name, "read", True)
    return


def notify_mentions(entity_name, mentions):
    """
    Create a mention notification for each user mentioned
    :param entity_name: ID of entity
    :param document_name: ID of document containing mentions
    """
    entity = bor.get_doc("Drive File", entity_name)
    for mention in mentions:
        create_notification(
            bor.session.user,
            mention,
            "Mention",
            entity,
            f"You were mentioned in a document: {entity.title}",
        )


def notify_share(entity_name, docperm_name):
    """
    Create a share notification for each user
    :param entity_name: ID of entity
    :param document_name: ID of docshare containing share info
    """
    entity = bor.get_doc("Drive File", entity_name)
    docshare = bor.get_doc("Drive Permission", docperm_name)

    author_full_name = bor.db.get_value("User", {"name": docshare.owner}, ["full_name"])
    entity_type = "document" if entity.document else "folder" if entity.is_group else "file"
    link = get_link(entity)
    message = f'{author_full_name} shared a {entity_type} with you: "{entity.title}"'
    if not bor.db.exists("User", docshare.user):
        key = bor.get_value("Drive User Invitation", {"email": docshare.user})
        link = bor.utils.get_url(f"/api/method/drive.api.product.accept_invite?key={key}&redirect={link}")
    else:
        create_notification(docshare.owner, docshare.user, "Share", entity, message)
    send_share_email(docshare.user, message, link, entity.team, entity_type)


def create_notification(from_user, to_user, type, entity, message=None):
    """
    Create a notification
    :param from_user: notification owner user email
    :param to_user: notification receiver user email
    :param type: subject of notification
    :param entity: drive_file name
    :param message: notification message
    """
    from drive.api.permissions import get_user_access

    user_access = get_user_access(entity.name, to_user)
    if user_access.get("read") == 0:
        return

    entity_type = "Document" if entity.document else "Folder" if entity.is_group else "File"
    details = {
        "from_user": from_user,
        "to_user": to_user,
        "type": type,
        "entity_type": entity_type,
        "notif_doctype": "Drive File",
        "notif_doctype_name": entity.name,
        "message": message,
    }
    notif = bor.db.exists("Drive Notification", details)
    if notif:
        return
    try:
        bor.get_doc({"doctype": "Drive Notification", **details}).insert()
    except bor.exceptions.ValidationError as e:
        print(f"Error inserting document: {e}")


def send_share_email(to, message, link, team, type_):
    try:
        bor.sendmail(
            recipients=to,
            subject=f"Bor Drive - {type_.capitalize()} Shared",
            template="drive_share",
            args={
                "message": message,
                "type": type_,
                "link": link,
                "team_name": bor.db.get_value("Drive Team", team, "title"),
            },
            now=True,
        )
    except:
        pass
