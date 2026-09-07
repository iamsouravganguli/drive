import bor


def after_install():
    if bor.db.db_type == "postgres":
        exists = bor.db.sql(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'drive_file_title_fts_idx'"
        )
        if not exists:
            bor.db.sql(
                'CREATE INDEX drive_file_title_fts_idx ON "tabDrive File" USING gin (to_tsvector(\'english\', title))'
            )
    else:
        index_check = bor.db.sql("""SHOW INDEX FROM `tabDrive File` WHERE Key_name = 'drive_file_title_fts_idx'""")
        if not index_check:
            bor.db.sql("""ALTER TABLE `tabDrive File` ADD FULLTEXT INDEX drive_file_title_fts_idx (title)""")
