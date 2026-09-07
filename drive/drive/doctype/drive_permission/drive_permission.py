# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import bor
from bor.model.document import Document

from drive.api.notifications import notify_share


class DrivePermission(Document):
    def after_insert(self):
        if self.user:
            bor.enqueue(
                notify_share,
                queue="short",
                job_id=f"fdocperm_{self.name}",
                deduplicate=True,
                timeout=None,
                now=True,
                at_front=False,
                entity_name=self.entity,
                docperm_name=self.name,
            )
