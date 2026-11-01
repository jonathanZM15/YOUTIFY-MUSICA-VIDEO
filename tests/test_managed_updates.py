import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from core.managed_updates import ManagedUpdates, valid_package_url
from core.storage import JsonStore
from core.updater import ReleaseInfo, Updater
from config.settings import GITHUB_REPO, UPDATE_ASSET_NAME, APP_VERSION


class Response(io.BytesIO):
    status = 200
    def geturl(self):
        return 'https://release-assets.githubusercontent.com/example/package.zip'


def package(version='9.0.0', extra=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('Youtify/update-manifest.json', json.dumps(dict(schema=1, app='Youtify', version=version, platform='win-x64', entrypoint='Youtify.exe')))
        for name in ('Youtify.exe', 'ffmpeg/ffmpeg.exe', 'ffmpeg/ffprobe.exe', 'runtime/node.exe'):
            z.writestr('Youtify/'+name, b'test executable')
        for name, value in (extra or {}).items():
            z.writestr(name, value)
    return buffer.getvalue()


def release(data, version='9.0.0'):
    return ReleaseInfo('v'+version, version, 'New version', '',
        f'https://github.com/{GITHUB_REPO}/releases/tag/v{version}',
        f'https://github.com/{GITHUB_REPO}/releases/download/v{version}/{UPDATE_ASSET_NAME}',
        hashlib.sha256(data).hexdigest(), len(data))


class TestManagedUpdates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = package()
        self.opener = Mock(side_effect=lambda *a, **k: Response(self.data))
        self.probe = Mock(return_value=dict(version='9.0.0', frozen=True, ffmpeg=True, ffprobe=True, javascript=True, ejs=True, icon=True))
        self.service = ManagedUpdates(self.root/'versions', JsonStore(self.root/'active.json'),
            current_version='1.0.0', opener=self.opener, probe=self.probe)

    def tearDown(self):
        self.temp.cleanup()

    def test_verified_package_is_activated_and_reused_without_redownload(self):
        executable = self.service.prepare(release(self.data))
        self.assertEqual(executable, self.service.ready_executable())
        self.assertTrue(executable.is_file())
        self.service.prepare(release(self.data))
        self.opener.assert_called_once()
        self.assertEqual(self.service.pointer.read()['previous'], {})
        self.assertFalse(list((self.root/'versions').glob('staging-*')))

    def test_bad_sha_never_activates_or_leaves_partial_files(self):
        info = release(self.data)
        info.sha256 = '0'*64
        with self.assertRaises(ValueError): self.service.prepare(info)
        self.assertFalse((self.root/'active.json').exists())
        self.assertEqual(list((self.root/'versions').iterdir()), [])
        self.probe.assert_not_called()

    def test_unsafe_zip_paths_and_case_collisions_rejected(self):
        for name in ('../escape.exe', 'Youtify/../../escape.exe', '/Youtify/a', 'Youtify/C:/a', 'Youtify/YOUTIFY.EXE', 'Youtify/NUL', 'Youtify/Youtify.exe.'):
            with self.subTest(name=name):
                self.data = package(extra={name:b'bad'})
                with self.assertRaises(ValueError): self.service.prepare(release(self.data))
                self.assertFalse((self.root/'active.json').exists())

    def test_manifest_and_runtime_must_match_version(self):
        self.data = package(version='8.0.0')
        with self.assertRaises(ValueError): self.service.prepare(release(self.data))
        self.data = package()
        self.probe.return_value['ffmpeg'] = False
        with self.assertRaises(ValueError): self.service.prepare(release(self.data))
        self.assertFalse((self.root/'active.json').exists())

    def test_truncated_download_and_untrusted_redirect_rejected(self):
        info = release(self.data)
        info.size += 1
        with self.assertRaises(ValueError): self.service.prepare(info)
        with patch.object(Response, 'geturl', return_value='https://evil.example/package.zip'):
            with self.assertRaises(ValueError): self.service.prepare(release(self.data))

    def test_altered_executable_is_not_launched(self):
        executable = self.service.prepare(release(self.data))
        executable.write_bytes(b'changed')
        self.assertIsNone(self.service.ready_executable())
        launcher = Mock()
        self.assertFalse(self.service.redirect(frozen=True, launcher=launcher))
        launcher.assert_not_called()

    def test_redirect_releases_lock_before_start_and_preserves_previous_on_failure(self):
        self.service.pointer.write({'version':'0.9.0','source':GITHUB_REPO})
        executable = self.service.prepare(release(self.data))
        calls = []
        self.assertTrue(self.service.redirect(frozen=True, release_lock=lambda:calls.append('unlock'),
            launcher=lambda *a,**kw:calls.append(('launch',a[0]))))
        self.assertEqual(calls, ['unlock', ('launch', [str(executable)])])
        with self.assertLogs('core.managed_updates', level='ERROR'):
            self.assertFalse(self.service.redirect(frozen=True, launcher=Mock(side_effect=OSError('test failure'))))
        self.assertEqual(self.service.pointer.read()['version'], '0.9.0')

    def test_development_or_already_current_does_not_redirect(self):
        self.service.prepare(release(self.data))
        self.assertFalse(self.service.redirect(frozen=False))
        self.service.current_version = '9.0.0'
        self.assertIsNone(self.service.ready_executable())

    def test_unreadable_update_never_prevents_startup(self):
        with patch.object(self.service, 'ready_executable', side_effect=PermissionError('locked')):
            with self.assertLogs('core.managed_updates', level='ERROR'):
                self.assertFalse(self.service.redirect(frozen=True))

    def test_only_expected_repository_package_is_allowed(self):
        url = release(self.data).download_url
        self.assertTrue(valid_package_url(url, 'v9.0.0'))
        for bad in (url.replace('https:', 'http:'), url.replace(GITHUB_REPO,'attacker/repo'), url.replace('.zip','.exe'), url.replace('github.com','github.com.evil.example')):
            self.assertFalse(valid_package_url(bad,'v9.0.0'))


class TestUpdateNotifications(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = patch('core.updater.UPDATE_STATE_FILE', Path(self.temp.name)/'state.json')
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.temp.cleanup()

    def test_notice_is_once_per_version_and_persists(self):
        self.assertTrue(Updater.should_notify('v9.0.0'))
        Updater._update_state(last_notified_tag='v9.0.0')
        self.assertFalse(Updater.should_notify('v9.0.0'))
        self.assertTrue(Updater.should_notify('v9.0.1'))

    def api_data(self):
        info = release(package())
        return dict(tag_name=info.tag_name, assets=[dict(name=UPDATE_ASSET_NAME, browser_download_url=info.download_url,
            size=info.size, digest='sha256:'+info.sha256)])

    def test_check_throttled_across_restarts_and_only_selects_zip(self):
        data = self.api_data()
        with patch('core.updater.urllib.request.urlopen', side_effect=lambda *a,**k:Response(json.dumps(data).encode())) as network:
            result = Updater.check_github_release()
            self.assertEqual(result.version, '9.0.0')
            self.assertTrue(result.download_url.endswith(UPDATE_ASSET_NAME))
            self.assertIsNone(Updater.check_github_release())
            network.assert_called_once()

    def test_no_update_same_version_or_missing_checksum_does_not_notify(self):
        for change in ('current', 'no_sha', 'no_zip', 'prerelease'):
            data = self.api_data()
            if change=='current': data['tag_name']='v'+APP_VERSION
            elif change=='no_sha': data['assets'][0].pop('digest')
            elif change=='no_zip': data['assets'][0]['name']='Youtify-Setup.exe'
            else: data['prerelease']=True
            Updater._write_update_state({})
            with patch('core.updater.urllib.request.urlopen', side_effect=lambda *a,**k:Response(json.dumps(data).encode())):
                self.assertIsNone(Updater.check_github_release())

    def test_background_notice_follows_successful_verification_only(self):
        info = release(package())
        callback = Mock()
        def run_immediately(**kwargs):
            return Mock(start=kwargs['target'])
        with patch('core.updater.sys.frozen', True, create=True), \
                patch('core.updater.threading.Thread', side_effect=run_immediately), \
                patch.object(Updater, 'check_github_release', return_value=info), \
                patch('core.managed_updates.ManagedUpdates.prepare') as prepare:
            prepare.side_effect = ValueError('checksum failed')
            with self.assertLogs('core.updater', level='ERROR'):
                Updater.check_app_update_async(callback)
            callback.assert_not_called()
            prepare.side_effect = None
            Updater.check_app_update_async(callback)
            callback.assert_called_once_with(info)

    def test_development_never_downloads_a_packaged_update(self):
        with patch('core.updater.sys.frozen', False, create=True), \
                patch('core.updater.threading.Thread', side_effect=lambda **kw:Mock(start=kw['target'])), \
                patch.object(Updater, 'check_github_release') as check:
            Updater.check_app_update_async(Mock())
            check.assert_not_called()
