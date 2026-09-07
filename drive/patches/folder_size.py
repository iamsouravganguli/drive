import bor


def scan(folder):
    folder = bor.get_doc("Drive File", folder)
    child_folders = bor.get_list("Drive File", {"parent_entity": folder.name, "is_group": 1}, pluck="name")
    for child in child_folders:
        scan(child)
    sizes = bor.get_list("Drive File", {"parent_entity": folder.name, "is_active": 1}, pluck="file_size")
    bor.db.set_value("Drive File", folder.name, "file_size", sum(sizes), update_modified=False)


def execute():
    roots = bor.get_list("Drive File", {"parent_entity": ""}, pluck="name")
    for root in roots:
        scan(root)
