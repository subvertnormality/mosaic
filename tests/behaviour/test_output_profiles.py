"""Loader rejection contracts; native workflow coverage lives in output_cases."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import driver

class OutputProfiles(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.mods=self.root/'mods';self.mods.mkdir()
        self.source=self.mods/'nb_jf'
        original=Path(os.environ['MOSAIC_OUTPUT_MOD_ROOT'])/'nb_jf'
        subprocess.run(['git','clone','--shared','--quiet',str(original),str(self.source)],check=True)
        self.git('remote','set-url','origin','https://github.com/sixolet/nb_jf.git')
        self.git('checkout','--quiet','--detach','fc0922feb5f8e91f7732602a3b99716bf7099e78')
    def git(self,*args):
        return subprocess.check_output(['git',*args],cwd=self.source,text=True).strip()
    def rejected(self,pattern,**kwargs):
        out=self.root/'run';out.mkdir()
        with patch.object(driver,'Session',side_effect=AssertionError('Native session must not start')) as session:
            with self.assertRaisesRegex(ValueError,pattern):
                driver.Driver(out,profile='crow-jf',mod_code_root=self.mods,**kwargs)
            session.assert_not_called()
    def test_wrong_origin(self):
        self.git('remote','set-url','origin','https://example.invalid/wrong.git')
        self.rejected('Unexpected mod origin')
    def test_wrong_revision(self):
        self.git('checkout','--quiet','--detach','HEAD^')
        self.rejected('Unexpected mod revision')
    def test_tracked_edit(self):
        p=self.source/'lib/mod.lua';p.write_text(p.read_text()+'\n-- changed fixture\n')
        self.rejected('uncommitted changes')
    def test_untracked_lua(self):
        (self.source/'unexpected.lua').write_text('return {}\n')
        self.rejected('uncommitted changes')
    def test_ignored_runtime_source(self):
        # A local exclude cannot make an extra loadable Lua file match the pin.
        with (self.source/'.git/info/exclude').open('a') as stream:stream.write('\nignored.lua\n')
        (self.source/'ignored.lua').write_text('return {}\n')
        self.rejected('Ignored runtime source')
    def test_controlled_rejected_before_launch(self):
        self.rejected('require real time',clock_mode='controlled-experimental')
    def test_missing_capability_closes_owned_session(self):
        out=self.root/'run';out.mkdir()
        with patch.object(driver,'Session') as factory:
            session=factory.return_value
            session.info={'data':str(out/'data'),'application_identity':{}}
            session.capabilities.return_value={'supported':[]}
            with self.assertRaisesRegex(ValueError,'Missing required output capability: Just Friends'):
                driver.Driver(out,profile='crow-jf',mod_code_root=self.mods)
            factory.assert_called_once()
            self.assertEqual(factory.call_args.kwargs['enabled_mods'],['nb_jf'])
            session.close.assert_called_once_with(out/'native')

    def test_missing_source(self):
        absent=self.root/'absent';absent.mkdir();out=self.root/'run';out.mkdir()
        with patch.object(driver,'Session') as session:
            with self.assertRaisesRegex(ValueError,'Missing mod source'):
                driver.Driver(out,profile='crow-jf',mod_code_root=absent)
            session.assert_not_called()

if __name__=='__main__':unittest.main()
