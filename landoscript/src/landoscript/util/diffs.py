from difflib import unified_diff


def diff_contents(orig, modified, file):
    """Create a git-style unified diff of `orig` and `modified` with the filename `file`."""
    add_remove_metadata = ""
    if orig:
        # orig exists already
        orig_contents = orig.splitlines()
        fromfile = f"a/{file}"
    else:
        # orig does not exist yet; ie: it will be added
        orig_contents = ""
        fromfile = "/dev/null"
        add_remove_metadata = "new file mode 100644\n"
    if modified:
        # modified exists already
        modified_contents = modified.splitlines()
        tofile = f"b/{file}"
    else:
        # modified does not exist yet; ie: it will be added
        modified_contents = ""
        tofile = "/dev/null"
        add_remove_metadata = "deleted file mode 100644\n"

    diff = ""
    # header line always uses the same filename twice - even with additions and removals
    diff += f"diff --git a/{file} b/{file}\n{add_remove_metadata}"
    diff += "\n".join(unified_diff(orig_contents, modified_contents, fromfile=fromfile, tofile=tofile, lineterm=""))
    # preserve the newline at the end of the new version of the file, if it exists
    if modified:
        if modified.endswith("\n"):
            diff += "\n"
        else:
            diff += "\n\\ No newline at end of file\n"
    # otherwise, make sure the removal is correctly line ended
    else:
        if orig.endswith("\n"):
            diff += "\n"
        else:
            diff += "\n\\ No newline at end of file\n"

    return diff
