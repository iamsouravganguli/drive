import bor


def presentation(doc, event):
    file = bor.get_value("Drive File", {"path": doc.name}, "name")

    if file:
        if event == "on_update":
            bor.get_doc("Drive File", file).rename(doc.title)
        if event == "on_trash":
            print("gone, boom boom")
            bor.get_doc("Drive File", file).permanent_delete()
