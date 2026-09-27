"""Validate the executable bundle without making installation/staging copies."""
from pathlib import Path
import plistlib
import subprocess
import struct
import hashlib
import sys
import unittest

BUILD = Path(sys.argv.pop(1)).resolve()


class BundleTests(unittest.TestCase):
    def test_single_self_contained_application(self):
        app = BUILD / 'bin/Alright.app'
        self.assertEqual(list(BUILD.rglob('*.app')), [app])
        with (app / 'Contents/Info.plist').open('rb') as stream:
            info = plistlib.load(stream)
        self.assertEqual(info['CFBundleIdentifier'], 'com.iisacc.Alright')
        self.assertEqual(info['CFBundlePackageType'], 'APPL')
        self.assertEqual(info['CFBundleIconFile'], 'Alright.icns')
        templates = app / 'Contents/Resources/DocumentTemplates'
        for name, signature in [('Blank.aiprivate', b'%!PS-Adobe'), ('Blank.aimetadata', b'%!PS-Adobe')]:
            data = (templates / name).read_bytes()
            source = (BUILD.parent / 'resources/DocumentTemplates' / name).read_bytes()
            self.assertTrue(data.startswith(signature))
            self.assertEqual(hashlib.sha256(data).digest(), hashlib.sha256(source).digest())
        icon = (app / 'Contents/Resources' / info['CFBundleIconFile']).read_bytes()
        self.assertEqual(icon[:4], b'icns')
        self.assertEqual(struct.unpack('>I', icon[4:8])[0], len(icon))
        representations = set()
        offset = 8
        while offset < len(icon):
            kind, length = struct.unpack('>4sI', icon[offset:offset + 8])
            self.assertGreaterEqual(length, 8)
            representations.add(kind)
            offset += length
        self.assertEqual(offset, len(icon))
        self.assertTrue({b'ic07', b'ic08', b'ic09', b'ic10'}.issubset(representations))
        executable = app / 'Contents/MacOS' / info['CFBundleExecutable']
        self.assertTrue(executable.is_file())
        dependencies = subprocess.check_output(['/usr/bin/otool', '-L', str(executable)], text=True)
        for line in dependencies.splitlines()[1:]:
            dependency = line.strip().split(' (', 1)[0]
            self.assertTrue(dependency.startswith(('/System/Library/', '/usr/lib/')), dependency)
        subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(app)], check=True)
        extension = app / 'Contents/PlugIns/AlrightFinderSync.appex'
        with (extension / 'Contents/Info.plist').open('rb') as stream:
            plugin = plistlib.load(stream)
        self.assertEqual(plugin['NSExtension']['NSExtensionPointIdentifier'], 'com.apple.FinderSync')
        self.assertEqual(plugin['NSExtension']['NSExtensionPrincipalClass'], 'AlrightFinderSync')
        subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(extension)], check=True)
        for binary in (executable, extension / 'Contents/MacOS/AlrightFinderSync'):
            build = subprocess.check_output(['/usr/bin/xcrun', 'vtool', '-show-build', str(binary)], text=True)
            self.assertIn('minos 14.0', build)
            symbols = subprocess.check_output(['/usr/bin/nm', str(binary)], text=True)
            self.assertIn('_swift_', symbols)
            self.assertEqual([p.name for p in binary.parent.iterdir()], [binary.name])
        groups = []
        for bundle in (app, extension):
            raw = subprocess.check_output(['/usr/bin/codesign', '-d', '--entitlements', ':-', str(bundle)], stderr=subprocess.DEVNULL)
            entitlements = plistlib.loads(raw)
            self.assertEqual(entitlements.get('com.apple.security.app-sandbox', False), bundle == extension)
            groups.append(entitlements['com.apple.security.application-groups'])
        self.assertEqual(groups[0], groups[1])


if __name__ == '__main__':
    unittest.main()
