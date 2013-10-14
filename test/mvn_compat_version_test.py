import unittest
import shutil
from test_common import *

class Test_mvn_compat_version(unittest.TestCase):

    def setUp(self):
        self.maxDiff = 2048
        dirpath = os.path.dirname(os.path.realpath(__file__))
        self.olddir = os.getcwd()
        self.workdir = os.path.join(dirpath, 'workdir')
        os.mkdir(self.workdir)
        os.chdir(self.workdir)

    def tearDown(self):
        try:
            shutil.rmtree(self.workdir)
        except OSError:
            pass
        os.chdir(self.olddir)

    @xmvnconfig('mvn_compat_version', [])
    def test_run_no_args(self, stdout, stderr, return_value):
        self.assertNotEqual(return_value, 0)
        self.assertEqual("Usage:", stderr[:6])

    @xmvnconfig('mvn_compat_version', ['-h'])
    def test_help(self, stdout, stderr, return_value):
        self.assertTrue(stdout)

    @xmvnconfig('mvn_compat_version',['aaa:bbb', '1', ])
    def test_simple(self, stdout, stderr, return_value):
        self.assertEquals(return_value, 0)
        filelist = get_config_file_list()
        self.assertEquals(len(filelist), get_expected_file_count('mvn_compat_version', 'simple'))
        for file in filelist:
            self.assertEquals(get_actual_config(file), get_expected_config(file, 'mvn_compat_version', 'simple'))

    @xmvnconfig('mvn_compat_version',['aaa:bbb', ])
    def test_single(self, stdout, stderr, return_value):
        self.assertNotEqual(return_value, 0)
        self.assertTrue(stderr)

    @xmvnconfig('mvn_compat_version',['aaa:bbb', '1', '2', '3', ])
    def test_more(self, stdout, stderr, return_value):
        self.assertEquals(return_value, 0)
        filelist = get_config_file_list()
        self.assertEquals(len(filelist), get_expected_file_count('mvn_compat_version', 'more'))
        for file in filelist:
            self.assertEquals(get_actual_config(file), get_expected_config(file, 'mvn_compat_version', 'more'))

    @xmvnconfig('mvn_compat_version',['aaa:bbb:ccc:ddd:1.2', '3.1', ])
    def test_version(self, stdout, stderr, return_value):
        self.assertEquals(return_value, 0)
        filelist = get_config_file_list()
        self.assertEquals(len(filelist), get_expected_file_count('mvn_compat_version', 'version'))
        for file in filelist:
            self.assertEquals(get_actual_config(file), get_expected_config(file, 'mvn_compat_version', 'version'))

    @xmvnconfig('mvn_compat_version',[':bbb', '2', ])
    def test_wildcard(self, stdout, stderr, return_value):
        self.assertEquals(return_value, 0)
        filelist = get_config_file_list()
        self.assertEquals(len(filelist), get_expected_file_count('mvn_compat_version', 'wildcard'))
        for file in filelist:
            self.assertEquals(get_actual_config(file), get_expected_config(file, 'mvn_compat_version', 'wildcard'))

    @xmvnconfig('mvn_compat_version',['aa:bb:{1,2}', '@1', ])
    def test_backref1(self, stdout, stderr, return_value):
        self.assertEquals(return_value, 0)
        filelist = get_config_file_list()
        self.assertEquals(len(filelist), get_expected_file_count('mvn_compat_version', 'backref1'))
        for file in filelist:
            self.assertEquals(get_actual_config(file), get_expected_config(file, 'mvn_compat_version', 'backref1'))

    @xmvnconfig('mvn_compat_version',['aaa:bb:{1,2}', '@3', ])
    def test_backref2(self, stdout, stderr, return_value):
        self.assertNotEqual(return_value, 0)
        self.assertTrue(stderr)

    @xmvnconfig('mvn_compat_version',['aaa:bbb:{1,2', '@1', ])
    def test_odd_braces1(self, stdout, stderr, return_value):
        self.assertNotEqual(return_value, 0)
        self.assertTrue(stderr)

    @xmvnconfig('mvn_compat_version',['aaa:bbb:1,2}', '@3', ])
    def test_odd_braces2(self, stdout, stderr, return_value):
        self.assertNotEqual(return_value, 0)
        self.assertTrue(stderr)

if __name__ == '__main__':
    unittest.main()
