from difflib import unified_diff


def diff_contents(orig, modified, file):
    diff = ""
    fromfile = f"a/{file}"
    tofile = f"b/{file}"
    diff += f"diff --git {fromfile} {tofile}\n"
    diff += "\n".join(unified_diff(orig.splitlines(), modified.splitlines(), fromfile=fromfile, tofile=tofile, lineterm=""))
    if orig.endswith("\n"):
        diff += "\n"

    return diff
