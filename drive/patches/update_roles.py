import bor


def execute():
    bor.reload_doc("Drive", "doctype", "Drive Team Member")
    for id in bor.get_all("Drive Team Member"):
        member = bor.get_doc("Drive Team Member", id)
        member.access_level = 2 if member.is_admin else 1
        member.save()
