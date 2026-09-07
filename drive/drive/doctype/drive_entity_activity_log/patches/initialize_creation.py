import bor


def execute():
    all_entities = bor.db.get_list("Drive File", fields=["name", "title", "owner", "creation"])

    for i in all_entities:
        doc = bor.new_doc("Drive Entity Activity Log")
        doc.entity = i.name
        doc.action_type = "create"
        doc.message = f"Created {i.title}"
        doc.save()
        bor.db.set_value("Drive Entity Activity Log", doc.name, "owner", i.owner)
        bor.db.set_value("Drive Entity Activity Log", doc.name, "creation", i.creation)
