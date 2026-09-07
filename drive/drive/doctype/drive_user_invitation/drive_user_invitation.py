# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import bor
from bor.model.document import Document
from bor.utils import add_days, get_datetime, now, validate_email_address

EXPIRY_DAYS = 1


class DriveUserInvitation(Document):
    def has_expired(self):
        return get_datetime(self.creation) < get_datetime(add_days(now(), -EXPIRY_DAYS))

    def before_insert(self):
        validate_email_address(self.email, True)

    def after_insert(self):
        if self.status == "Pending":
            try:
                self.invite_via_email()
            except BaseException as e:
                bor.log_error(f"Failed to send invite email: {e}")
                pass
        elif self.status == "Proposed":
            admins = bor.get_all("Drive Team Member", filters={"parent": self.team, "access_level": 2}, pluck="user")
            for admin in admins:
                bor.get_doc(
                    {
                        "doctype": "Drive Notification",
                        "to_user": admin,
                        "type": "Team",
                        "message": f"A person ({self.email}) from your domain has joined Bor Drive",
                    }
                ).insert(ignore_permissions=True)
            bor.db.commit()

    def invite_via_email(self):
        bor.sendmail(
            recipients=self.email,
            subject=f"Bor Drive - Invitation",
            template="drive_invitation",
            args={
                "invite_link": bor.utils.get_url(f"/api/method/drive.api.product.accept_invite?key={self.name}"),
                "user": bor.session.user,
                "team_name": bor.db.get_value("Drive Team", self.team, "title"),
            },
            now=True,
        )

    def accept(self, redirect=True):
        if self.status not in ["Pending", "Automatic"]:
            bor.throw("This key has already been used")
        if self.status == "Expired" or self.has_expired():
            self.status = "Expired"
            self.save(ignore_permissions=True)
            bor.db.commit()
            bor.throw("Invalid or expired key")

        exists = bor.db.exists(
            "Account Request",
            {
                "email": self.email,
                "signed_up": 1,
            },
        )

        if redirect:
            bor.local.response["type"] = "redirect"

        if not exists:
            # If the user does not have an account, redirect to sign up
            req = bor.get_doc(
                {
                    "doctype": "Account Request",
                    "email": self.email,
                    "invite": self.name,
                    "login_count": 1,
                }
            ).insert(ignore_permissions=True)
            bor.db.commit()
            user_exists = bor.db.exists("User", self.email)

            if not user_exists:
                team_name = bor.db.get_value("Drive Team", self.team, "title")
                url = f"/drive/signup?e={self.email}{'&t=' + team_name if team_name else ''}&r={req.name}"
                if isinstance(redirect, str):
                    url += f"&redirect-to={redirect}"
                bor.local.response["location"] = url
                return

        # Otherwise, add the user to the team
        team = bor.get_doc("Drive Team", self.team)
        team.append("users", {"user": self.email, "access_level": 0 if self.as_guest else 1})
        team.save(ignore_permissions=True)
        self.status = "Accepted"
        self.accepted_at = bor.utils.now()
        self.save(ignore_permissions=True)
        bor.db.commit()

        if bor.session.user == "Guest":
            bor.local.login_manager.login_as(self.email)

        bor.local.response["location"] = "/drive/t/" + self.team
        return "/drive/t/" + self.team
