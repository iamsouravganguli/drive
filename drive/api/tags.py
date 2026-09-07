import bor


@bor.whitelist()
def create_tag(title, color="gray"):
    """
    Create new tag for entity

    :param title: Tag name
    :param color: Tag color
    """

    doc = bor.get_doc(
        {
            "doctype": "Drive Tag",
            "title": title,
            "color": color,
        }
    )

    tag_exists = bor.db.exists({"doctype": "Drive Tag", "owner": bor.session.user, "title": title})
    if tag_exists:
        bor.throw("Tag already exists")
    doc.save()
    return doc.name


@bor.whitelist()
def add_tag(entity, tag):
    """
    Add tag to entity

    :param entity: Entity name
    :param tag: Tag name
    """
    doc = bor.get_doc("Drive File", entity)
    doc.append("tags", {"tag": tag})
    doc.save()


@bor.whitelist()
def get_entity_tags(entity):
    """
    Returns all tags of given entity

    :param entity: Entity name
    """

    entity = bor.get_doc("Drive File", entity)

    return map(
        lambda x: bor.db.get_value("Drive Tag", x.tag, ["name", "title", "color"], as_dict=1),
        entity.tags,
    )


@bor.whitelist()
def get_user_tags():
    """
    Returns all tags created by current user

    """
    return bor.db.get_list(
        "Drive Tag",
        fields=["name", "title", "color"],
    )


@bor.whitelist()
def get_tags_with_owner():
    """
    Returns all tags created by current user

    """
    return bor.db.get_list(
        "Drive Tag",
        fields=["name", "title", "color", "owner"],
        as_list=False,
    )


@bor.whitelist()
def edit_tag(tag, title, color):
    """
    Update color for givent tag

    :param tag: Tag name
    :param color: Color to be update with
    """
    doc = bor.get_doc("Drive Tag", tag)
    doc.title = title
    doc.color = color
    doc.save()


@bor.whitelist()
def remove_tag(entity, tag=None, all=False):
    """
    Remove tag from entity

    :param entity: Entity name
    :param tag: Tag name
    """

    entity_doc = bor.get_doc("Drive File", entity)
    for tag_doc in entity_doc.tags:
        if (tag_doc.tag == tag or all) and tag_doc.owner == bor.session.user:
            tag_doc.delete(ignore_permissions=True)


@bor.whitelist()
def delete_tag(tag):
    """
    Delete tag

    :param tag: Tag name
    """
    EntityTag = bor.qb.DocType("Drive File Tag")
    query = bor.qb.from_(EntityTag).select(EntityTag.name).where(EntityTag.tag == tag)
    result = query.run(as_dict=True)
    for i in result:
        bor.delete_doc("Drive File Tag", i.name)
    bor.delete_doc("Drive Tag", tag)
    return result
