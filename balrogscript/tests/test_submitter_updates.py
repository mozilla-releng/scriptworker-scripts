import unittest

from balrogscript.submitter.release import makeCandidatesDir


class TestCandidatesDir(unittest.TestCase):
    def test_base(self):
        expected = "/pub/bbb/candidates/1.0-candidates/build2/"
        got = makeCandidatesDir("bbb", "1.0", 2)
        self.assertEqual(expected, got)

    def test_fennec(self):
        expected = "/pub/mobile/candidates/15.1-candidates/build3/"
        got = makeCandidatesDir("fennec", "15.1", 3)
        self.assertEqual(expected, got)

    def test_remote(self):
        expected = "http://foo.bar/pub/bbb/candidates/1.0-candidates/build5/"
        got = makeCandidatesDir("bbb", "1.0", 5, protocol="http", server="foo.bar")
        self.assertEqual(expected, got)

    def test_ftp_root(self):
        expected = "pub/bbb/candidates/1.0-candidates/build5/"
        got = makeCandidatesDir("bbb", "1.0", 5, ftp_root="pub/")
        self.assertEqual(expected, got)
