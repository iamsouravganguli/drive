import bor


@bor.whitelist()
def convert_pm_to_md(obj):
    from pmconverter import prose2markdown

    return prose2markdown(obj)


@bor.whitelist()
def get_yjs_content(entity_name):
    return bor.get_value("Drive Document", bor.get_value("Drive File", entity_name, "document"), "content")


from markdownify import markdownify as md


@bor.whitelist()
def sync_to_wiki_page(wiki_space, group, entity_name, html):
    title = bor.get_value("Drive File", entity_name, "title")
    content = md(html)
    route = group.lower().replace(" ", "-") + "/" + title.lower().replace(" ", "-")
    existing_page = bor.db.exists("Wiki Page", {"route": route})
    if existing_page:
        bor.get_doc("Wiki Page", existing_page).update({"content": content}).save()
    else:
        page = bor.get_doc(
            {
                "doctype": "Wiki Page",
                "title": title,
                "route": route,
                "wiki_space": wiki_space,
                "content": content,
            }
        )
        page.insert(ignore_permissions=True)
        space = bor.get_doc("Wiki Space", wiki_space)
        space.append("wiki_sidebars", {"parent_label": group, "wiki_page": page.name})
        space.save()

    return content


@bor.whitelist()
def sync_space(folder, wiki_space):
    bor.publish_realtime("chill", {"msg": "Syncing to wiki..."})
    # Get all groups (subfolders) and pages (nested documents) in this folder
    groups = bor.get_all(
        "Drive File",
        filters={"parent_entity": folder, "is_group": 1},
        fields=["name", "title"],
    )
    res = {}
    for g in groups:
        res[g.title] = bor.get_all(
            "Drive File",
            filters={"parent_entity": g.name},
            pluck="name",
        )
    return bor.publish_realtime("sync_to_wiki", {"space": wiki_space, "groups": res})
