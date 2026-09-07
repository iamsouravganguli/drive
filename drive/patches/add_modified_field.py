import bor


def execute():
    for k in bor.get_all("Drive File", fields=["name", "modified"]):
        bor.db.set_value(
            "Drive File",
            k.name,
            "_modified",
            k.modified.strftime("%Y-%m-%d %H:%M:%S.%f"),
            update_modified=False,
        )
