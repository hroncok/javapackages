import unittest

from test_common import *


class TestOSGiProv(unittest.TestCase):

    @osgiprov(["/usr/bin/zip"])
    def test_rhbz889131(self, stdout, stderr, return_value):
        self.assertEqual(return_value, 0, stderr)
        sout = [x for x in stdout.split('\n') if x]
        self.assertEqual(len(sout), 0)

    @osgiprov(["data/osgi/basic/buildroot/usr/share/META-INF/MANIFEST.MF",
               "data/osgi/basic/buildroot/"])
    def test_basic(self, stdout, stderr, return_value):
        self.assertEqual(return_value, 0, stderr)
        sout = [x for x in stdout.split('\n') if x]
        assertIn(self, "osgi(org.junit) = 4.10.0", sout)

    @osgiprov(["data/osgi/basic_jar/buildroot/usr/lib/basic.jar",
               "data/osgi/basic_jar/buildroot/"])
    def test_basic_jar(self, stdout, stderr, return_value):
        self.assertEqual(return_value, 0, stderr)
        sout = [x for x in stdout.split('\n') if x]
        assertIn(self, "osgi(org.junit) = 4.10.0", sout)

    @osgiprov(["data/osgi/empty/buildroot/usr/share/META-INF/MANIFEST.MF",
               "data/osgi/empty/buildroot/"])
    def test_empty(self, stdout, stderr, return_value):
        self.assertEqual(return_value, 0, stderr)
        sout = [x for x in stdout.split('\n') if x]
        self.assertEqual(len(sout), 0)


if __name__ == '__main__':
    unittest.main()
