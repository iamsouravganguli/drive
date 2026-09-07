import bor


def execute():
    for user in bor.db.get_list("User", pluck="name"):
        teams = bor.get_all(
            "Drive Team Member",
            pluck="parent",
            filters=[
                ["parenttype", "=", "Drive Team"],
                ["user", "=", user],
            ],
        )
        if teams:
            if not bor.db.exists("Drive Settings", {"user": user}):
                bor.get_doc(
                    {
                        "doctype": "Drive Settings",
                        "user": user,
                        "single_click": 1,
                        "default_team": teams[0],
                    }
                ).insert()
