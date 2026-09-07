import bor


def execute():
    settings = bor.get_single("Drive Disk Settings")
    settings.flat = True
    settings.save()
