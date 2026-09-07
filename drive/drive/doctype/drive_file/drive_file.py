import shutil
from pathlib import Path

import bor
from bor.model.document import Document
from bor.utils import now

from drive.api.activity import create_new_activity_log
from drive.api.files import get_new_title
from drive.api.permissions import get_user_access, user_has_permission
from drive.api.product import invite_users
from drive.utils import generate_upward_path, get_home_folder, update_file_size, update_clients
from drive.utils.files import FileManager
from drive.utils.api import prettify_file


class DriveFile(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def manager(self):
        return FileManager()

    def after_insert(self):
        full_name = bor.db.get_value("User", {"name": bor.session.user}, ["full_name"])
        message = f"{full_name} created {self.title}"
        create_new_activity_log(
            entity=self.name,
            activity_type="create",
            activity_message=message,
            document_field="title",
            field_new_value=self.title,
        )

    def on_trash(self):
        bor.db.delete("Drive Favourite", {"entity": self.name})
        bor.db.delete("Drive Entity Log", {"entity_name": self.name})
        bor.db.delete("Drive Permission", {"entity": self.name})
        bor.db.delete("Drive Notification", {"notif_doctype_name": self.name})
        bor.db.delete("Drive Entity Activity Log", {"entity": self.name})

        if self.is_group or self.document:
            for child in self.get_children():
                has_write_access = user_has_permission(self, "write")
                child.delete(ignore_permissions=has_write_access)

    def after_delete(self):
        """Cleanup after entity is deleted"""
        if self.document:
            bor.delete_doc("Drive Document", self.document)

        # Don't delete files on disk
        # if self.path:
        #     self.manager.delete_file(self)

    def on_rollback(self):
        if self.flags.file_created:
            shutil.rmtree(self.path) if self.is_group else self.path.unlink()

    def get_children(self):
        """Return a generator that yields child Documents."""
        child_names = bor.get_list(self.doctype, filters={"parent_entity": self.name}, pluck="name")
        for name in child_names:
            yield bor.get_doc(self.doctype, name)

    def __update_modified(func):
        def decorator(self, *args, **kwargs):
            client = kwargs.pop("client", None)
            old_parent = self.parent_entity
            res = func(self, *args, **kwargs)
            bor.db.set_value("Drive File", self.name, "_modified", now())
            update_clients(self.name, self.team, func.__name__, client)
            if client:
                if func.__name__ == "rename":
                    bor.publish_realtime(
                        "client-rename",
                        {"entity_name": self.name, "title": self.title},
                    )
                elif func.__name__ == "move":
                    bor.publish_realtime(
                        "list-remove",
                        {"parent": old_parent, "entity_name": self.name},
                    )
                    bor.publish_realtime(
                        "list-add",
                        {"file": prettify_file(self.as_dict())},
                    )
            return res

        return decorator

    @__update_modified
    def move(self, new_parent=None, new_team=None):
        """
        Move file or folder to the new parent folder
        If not owned by current user, copies it.

        :param new_parent: Document-name of the new parent folder. Defaults to the user directory
        :raises NotADirectoryError: If the new_parent is not a folder, or does not exist
        :raises FileExistsError: If a file or folder with the same name already exists in the specified parent folder
        :return: DriveEntity doc once file is moved
        """
        if new_team and not new_parent:
            new_parent = new_parent or get_home_folder(new_team).name
        elif new_parent and not new_team:
            new_team = bor.db.get_value('Drive File', new_parent, 'team')
        elif not new_parent and not new_team:
            new_team = self.team
            new_parent = new_parent or get_home_folder(new_team).name

        if new_parent == self.name:
            bor.throw(
                "Cannot move into itself",
                bor.PermissionError,
            )
        if not (
            bor.db.get_value("Drive File", new_parent, "is_group")
            or bor.db.get_value("Drive File", new_parent, "document")
        ):
            bor.throw(
                "Can only move into folders",
                NotADirectoryError,
            )

        for child in self.get_children():
            if child.name == self.name or child.name == new_parent:
                bor.throw(
                    "Cannot move into itself",
                    ValueError,
                )
            elif new_team != child.team:
                child.move(self.name, new_team)

        if new_parent != self.parent_entity:
            update_file_size(self.parent_entity, -self.file_size)
            update_file_size(new_parent, +self.file_size)
            self.parent_entity = new_parent
            self.title = get_new_title(self.title, new_parent, self.is_group, self.name)

        self.team = new_team

        not_in_disk = self.document or self.mime_type == "bor/slides" or self.is_link

        # Condition is so that old file names aren't corrupted
        if not self.manager.flat and not not_in_disk:
            new_path = self.manager.get_disk_path(self)
            self.manager.move(self, str(new_path))
            self.recursive_path_move(self.path, new_path)
            self.path = new_path

        self.save()

        return bor.get_value("Drive File", new_parent, ["title", "team", "name", "parent_entity"], as_dict=True)

    @bor.whitelist()
    @__update_modified
    def rename(self, new_title):
        """
        Rename file or folder

        :param new_title: New file or folder name
        :raises FileExistsError: If a file or folder with the same name already exists in the parent folder
        :return: DriveEntity doc once it's renamed
        """
        if new_title == self.title:
            return self

        validated_name = get_new_title(new_title, self.parent_entity, self.is_group, self.name)
        if new_title != validated_name:
            return bor.throw(
                f"{'Folder' if self.is_group else 'File'} '{new_title}' already exists\n Try '{validated_name}' ",
                FileExistsError,
            )

        full_name = bor.db.get_value("User", {"name": bor.session.user}, ["full_name"])
        message = f"{full_name} renamed {self.title} to {new_title}"
        create_new_activity_log(
            entity=self.name,
            activity_type="rename",
            activity_message=message,
            document_field="title",
            field_old_value=self.title,
            field_new_value=new_title,
        )
        if len(new_title) > 140:
            bor.throw("Your title can't be more than 140 characters.")
        self.title = new_title
        path = self.manager.rename(self)

        if self.path and self.mime_type != "bor/slides":
            self.recursive_path_move(self.path, path)

        self.save()

    def recursive_path_move(self, old, new):
        if new:
            self.path = new
        for child in self.get_children():
            not_in_disk = child.mime_type == "bor/slides" or child.is_link
            if child.path and not not_in_disk:
                child.recursive_path_move(child.path, str(Path(new) / Path(child.path).relative_to(old)))
        self.save()

    @bor.whitelist()
    def change_color(self, new_color):
        """
        Change color of a folder

        :param new_color: New color selected for folder
        :raises InvalidColor: If the color is not a hex value string
        :return: DriveEntity doc once it's updated
        """
        return bor.db.set_value("Drive File", self.name, "color", new_color, update_modified=False)

    def permanent_delete(self):
        write_access = user_has_permission(self, "write")
        parent_write_access = user_has_permission(self.parent_entity, "write")

        if not (write_access or parent_write_access):
            bor.throw("Not permitted", bor.PermissionError)

        self.is_active = -1
        if self.is_group:
            for child in self.get_children():
                child.permanent_delete()
        self.save()

    @bor.whitelist()
    def share(
        self,
        user=None,
        read=None,
        comment=None,
        share=None,
        upload=None,
        write=None,
        team=False,
    ):
        if not user_has_permission(self, "share"):
            bor.throw("Not permitted to share", bor.PermissionError)

        # Clean out existing general records
        if not user or team:
            self.unshare("$GENERAL")

        permission = bor.db.get_value(
            "Drive Permission",
            {
                "entity": self.name,
                "user": user or "",
                "team": team,
            },
        )
        if not permission:
            permission = bor.new_doc("Drive Permission")
            permission.update(
                {
                    "user": user,
                    "team": team,
                    "entity": self.name,
                }
            )
        else:
            permission = bor.get_doc("Drive Permission", permission)

        # Create user
        if not bor.db.exists("User", user):
            invite_users(user, auto=True)

        levels = [
            ["read", read],
            ["comment", comment],
            ["share", share],
            ["upload", upload],
            ["write", write],
        ]
        permission.update({l[0]: l[1] for l in levels if l[1] is not None})

        permission.save(ignore_permissions=True)

    @bor.whitelist()
    def unshare(self, user=None):
        """Unshare this file or folder with the specified user
        :param user: User or group with whom this is to be shared
        :param user_type:
        """
        absolute_path = generate_upward_path(self.name)
        for i in absolute_path:
            if i["owner"] == user:
                bor.throw("User owns parent folder", bor.PermissionError)

        if user == "$GENERAL":
            perm_names = bor.db.get_list(
                "Drive Permission",
                {"entity": self.name},
                or_filters={"user": "", "team": 1},
                pluck="name",
            )
            for perm_name in perm_names:
                bor.delete_doc("Drive Permission", perm_name, ignore_permissions=True)

            # If overriding perms of a parent folder, write out an explicit denial
            public_access = get_user_access(self, "Guest")
            team_access = get_user_access(self, team=1)
            user = None
            if public_access["read"]:
                user = ""
            elif team_access["read"]:
                user = team_access["team"]

            # Doesn't work as higher access "overrides" in get_user_access
            if user is not None:
                bor.get_doc(
                    {
                        "doctype": "Drive Permission",
                        "user": user,
                        "entity": self.name,
                        "read": 0,
                        "comment": 0,
                        "share": 0,
                        "write": 0,
                        "team": bool(user),
                    }
                ).insert()

        else:
            perm_name = bor.db.get_value(
                "Drive Permission",
                {
                    "user": user,
                    "entity": self.name,
                },
            )
            if perm_name:
                bor.delete_doc("Drive Permission", perm_name, ignore_permissions=True)


def on_doctype_update():
    bor.db.add_index("Drive File", ["title"])
