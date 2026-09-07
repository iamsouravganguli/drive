# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import bor


def whitelist(fn):
    if not bor.conf.enable_ui_tests:
        bor.throw("Cannot run UI tests. Set 'enable_ui_tests' in site_config.json to continue.")

    whitelisted = bor.whitelist(allow_guest=True)(fn)
    return whitelisted


@whitelist
def clear_data():
    doctypes = bor.get_all("DocType", filters={"module": "Drive", "issingle": 0}, pluck="name")
    for doctype in doctypes:
        bor.db.delete(doctype)

    bor.set_user("Administrator")
    admin = bor.get_doc("User", "Administrator")
    admin.add_roles("Drive Admin")

    if not bor.db.exists("User", "four@test.io"):
        user = bor.get_doc(
            doctype="User",
            email="four@test.io",
            first_name="Four",
            last_name="McTest",
            send_welcome_email=0,
        )
        user.insert()

    keep_users = ["Administrator", "Guest", "four@test.io"]
    for user in bor.get_all("User", filters={"name": ["not in", keep_users]}):
        bor.delete_doc("User", user.name)
