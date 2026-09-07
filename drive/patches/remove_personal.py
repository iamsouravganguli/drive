import time
from pathlib import Path

import bor


def execute():
    print(
        "This migration to a beta release might CORRUPT your data. Do NOT run this before taking a complete backup. You have two minutes left to cancel this deployment. "
    )
    time.sleep(120) 

    bor.reload_doc("Drive", "doctype", "Drive Disk Settings")
    doc = bor.get_single("Drive Disk Settings")
    doc.team_prefix = "team_name"
    doc.preview_size = 100
    doc.save()

    bor.reload_doc("Drive", "doctype", "Drive Permission")

    # Change team shares
    for share in bor.get_list("Drive Permission", filters={"user": "$TEAM"}, fields=["name", "entity"]):
        team = bor.db.get_value("Drive File", share["entity"], "team")
        bor.db.set_value("Drive Permission", share["name"], "user", team)
        bor.db.set_value("Drive Permission", share["name"], "team", 1)

    if bor.get_value("Drive Permission", {"user": "$TEAM"}, "name"):
        raise ValueError("Not all perms migrated!")

    # Insert personal team for every user if not exists
    bor.reload_doc("Drive", "doctype", "Drive Team")
    MAP = {}
    for user in bor.get_all("User", pluck="name"):
        if user == "Guest":
            continue
        bor.session.user = user
        team = bor.db.exists({"doctype": "Drive Team", "personal": 1, "owner": user})
        if not team:
            team = bor.get_doc({"doctype": "Drive Team", "title": user, "personal": 1})
            team.insert()
            print(f"Created personal team {team.name} for user {user}")
            bor.db.set_value("Drive Team", team.name, "owner", user)
            MAP[user] = team.name
        else:
            print(f"Using pre-existing team {team} for {user}")
            MAP[user] = team

    bor.session.user = "Administrator"

    bor.reload_doc("Drive", "doctype", "Drive File")
    # Move all is_private files to personal team
    for f in bor.get_all(
        "Drive File",
        filters={"is_private": 1},
        fields=["name", "is_private", "owner", "parent_entity"],
    ):
        try:
            bor.db.set_value("Drive File", f.name, "team", MAP[f.owner], update_modified=False)
            # For root elements, change parent folder
            if not bor.db.get_value("Drive File", f.parent_entity, "parent_entity"):
                new_parent = bor.db.get_value("Drive File", {"team": MAP[f.owner], "parent_entity": None}, "name")
                bor.db.set_value("Drive File", f.name, "parent_entity", new_parent)
        except KeyError:
            print(f"There was an issue with the file {f} owned by {f.owner}")

    bor.db.commit()
