from difflib import unified_diff


def diff_contents(orig: str, modified: str, file: str) -> str:
    """Create a git-style unified diff of `orig` and `modified` with the filename `file`."""
    diff = ""
    fromfile = f"a/{file}"
    tofile = f"b/{file}"
    diff += f"diff --git {fromfile} {tofile}\n"
    diff += "\n".join(unified_diff(orig.splitlines(), modified.splitlines(), fromfile=fromfile, tofile=tofile, lineterm=""))
    if modified.endswith("\n"):
        diff += "\n"
    else:
        diff += "\n\\ No newline at end of file\n"

    return diff
