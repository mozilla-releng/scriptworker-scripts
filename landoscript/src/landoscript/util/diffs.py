from difflib import unified_diff

NO_NEWLINE_SUFFIX = "\\ No newline at end of file"


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

    diff_lines = [line for line in unified_diff(orig_contents, modified_contents, fromfile=fromfile, tofile=tofile, lineterm="")]
    if not diff_lines:
        return ""

    # Special handling is needed to make sure that the last line of a file
    # is handled correctly, regardless of whether or not it has a newline
    # at the end or not.
    if diff_lines[-1][0] == "+":
        # When the last line is being modified we need to look back an
        # additional line in the diff to see if the original version of the
        # line had a newline. (The first 3 entries in diff_lines are the diff
        # header, so we need to check for > 4 to see if there's a possible
        # prior version being removed.)
        if len(diff_lines) > 4:
            # If the second last line of the diff is a removal, and the
            # original file doesn't end with a newline, we need the special
            # suffix. (If it does end with a newline, it will get one when we
            # join the diff lines together further down.)
            if diff_lines[-2][0] == "-" and not orig.endswith("\n"):
                diff_lines.insert(-1, NO_NEWLINE_SUFFIX)
        # If the new version of the file ends with a newline, just add an empty
        # entry to the diff lines; the newline will be added when we join the
        # lines further join.
        if modified.endswith("\n"):
            diff_lines.append("")
        else:
            diff_lines.append(NO_NEWLINE_SUFFIX)
    else:
        # If the last line didn't start with a `+`, it means the last line is
        # either context, or this file is being removed. Either way, we just
        # need to look at the original file and either ensure there's a newline
        # or the special suffix.
        if orig.endswith("\n"):
            diff_lines.append("")
        else:
            diff_lines.append(NO_NEWLINE_SUFFIX)

    diff = ""
    # header line always uses the same filename twice - even with additions and removals
    diff += f"diff --git a/{file} b/{file}\n{add_remove_metadata}"
    diff += "\n".join(diff_lines)

    return diff
