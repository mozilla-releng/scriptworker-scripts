from landoscript.util.diffs import diff_contents


def test_no_differences():
    assert diff_contents("abc", "abc", "file.txt") == ""


def test_no_newline_at_end_of_file_before_side():
    before = "abcdef"
    after = "ghijkl\n"
    assert (
        diff_contents(before, after, "file.txt")
        == """\
diff --git a/file.txt b/file.txt
--- a/file.txt
+++ b/file.txt
@@ -1 +1 @@
-abcdef
\\ No newline at end of file
+ghijkl
"""
    )


def test_no_newline_at_end_of_file_after_side():
    before = "abcdef\n"
    after = "ghijkl"
    assert (
        diff_contents(before, after, "file.txt")
        == """\
diff --git a/file.txt b/file.txt
--- a/file.txt
+++ b/file.txt
@@ -1 +1 @@
-abcdef
+ghijkl
\\ No newline at end of file"""
    )


def test_no_newline_at_end_of_file_both_sides():
    before = "abcdef"
    after = "ghijkl"
    assert (
        diff_contents(before, after, "file.txt")
        == """\
diff --git a/file.txt b/file.txt
--- a/file.txt
+++ b/file.txt
@@ -1 +1 @@
-abcdef
\\ No newline at end of file
+ghijkl
\\ No newline at end of file"""
    )


def test_newline_at_end_of_file_both_sides():
    before = "abcdef\n"
    after = "ghijkl\n"
    assert (
        diff_contents(before, after, "file.txt")
        == """\
diff --git a/file.txt b/file.txt
--- a/file.txt
+++ b/file.txt
@@ -1 +1 @@
-abcdef
+ghijkl
"""
    )


def test_no_newline_removal():
    before = "abcdef"
    after = ""
    assert (
        diff_contents(before, after, "file.txt")
        == """\
diff --git a/file.txt b/file.txt
deleted file mode 100644
--- a/file.txt
+++ /dev/null
@@ -1 +0,0 @@
-abcdef
\\ No newline at end of file"""
    )


def test_no_newline_addition():
    before = ""
    after = "ghijkl"
    assert (
        diff_contents(before, after, "file.txt")
        == """\
diff --git a/file.txt b/file.txt
new file mode 100644
--- /dev/null
+++ b/file.txt
@@ -0,0 +1 @@
+ghijkl
\\ No newline at end of file"""
    )


def test_newline_removal():
    before = "abcdef\n"
    after = ""
    assert (
        diff_contents(before, after, "file.txt")
        == """\
diff --git a/file.txt b/file.txt
deleted file mode 100644
--- a/file.txt
+++ /dev/null
@@ -1 +0,0 @@
-abcdef
"""
    )


def test_newline_addition():
    before = ""
    after = "ghijkl\n"
    assert (
        diff_contents(before, after, "file.txt")
        == """\
diff --git a/file.txt b/file.txt
new file mode 100644
--- /dev/null
+++ b/file.txt
@@ -0,0 +1 @@
+ghijkl
"""
    )


def test_last_line_is_context_no_newline():
    before = "abc\nghi"
    after = "def\nghi"
    assert (
        diff_contents(before, after, "file.txt")
        == """\
diff --git a/file.txt b/file.txt
--- a/file.txt
+++ b/file.txt
@@ -1,2 +1,2 @@
-abc
+def
 ghi
\\ No newline at end of file"""
    )
