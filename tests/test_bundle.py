"""Validate the executable bundle without making installation/staging copies."""
from pathlib import Path
import plistlib
import subprocess
import struct
import hashlib
import sys
import unittest
import zlib

BUILD = Path(sys.argv.pop(1)).resolve()
CACHE = dict(line.split('=', 1) for line in (BUILD / 'CMakeCache.txt').read_text().splitlines()
             if line and not line.startswith(('#', '//')) and '=' in line)


def png_pixels(path):
    """Decode the 8-bit RGB/RGBA PNGs exported by Illustrator and AppKit."""
    data = path.read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError(f'{path} is not a PNG')
    compressed = bytearray()
    offset = 8
    while offset < len(data):
        length, kind = struct.unpack('>I4s', data[offset:offset + 8])
        chunk = data[offset + 8:offset + 8 + length]
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', chunk)
            if depth != 8 or color not in (2, 6) or (compression, filtering, interlace) != (0, 0, 0):
                raise ValueError(f'{path} must be a non-interlaced 8-bit RGB/RGBA PNG')
        elif kind == b'IDAT':
            compressed.extend(chunk)
        offset += length + 12
    channels = 4 if color == 6 else 3
    stride = width * channels
    raw = zlib.decompress(compressed)
    if len(raw) != height * (stride + 1):
        raise ValueError(f'{path} has an invalid PNG payload')
    previous = bytearray(stride)
    rows = []
    for y in range(height):
        start = y * (stride + 1)
        method = raw[start]
        row = bytearray(raw[start + 1:start + stride + 1])
        for i in range(stride):
            left = row[i - channels] if i >= channels else 0
            above = previous[i]
            upper_left = previous[i - channels] if i >= channels else 0
            if method == 1:
                predictor = left
            elif method == 2:
                predictor = above
            elif method == 3:
                predictor = (left + above) // 2
            elif method == 4:
                p = left + above - upper_left
                distances = (abs(p - left), abs(p - above), abs(p - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
            elif method == 0:
                predictor = 0
            else:
                raise ValueError(f'{path} has an unsupported PNG filter')
            row[i] = (row[i] + predictor) & 255
        rows.append(row)
        previous = row
    return width, height, channels, b''.join(rows)


class BundleTests(unittest.TestCase):
    def test_app_icon_master_and_representations(self):
        master = BUILD.parent / 'resources/AppIcon/Alright.png'
        width, height, channels, pixels = png_pixels(master)
        self.assertEqual((width, height), (1024, 1024))
        if channels == 4:
            self.assertEqual(set(pixels[3::4]), {255}, 'The master must be opaque through every edge.')
        iconset = BUILD / 'generated/Alright.iconset'
        expected = set()
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                name = f'icon_{size}x{size}{"@2x" if scale == 2 else ""}.png'
                expected.add(name)
                with self.subTest(name=name):
                    width, height, channels, pixels = png_pixels(iconset / name)
                    self.assertEqual((width, height), (size * scale, size * scale))
                    if channels == 4:
                        self.assertEqual(set(pixels[3::4]), {255}, 'Resampling must retain the full opaque square.')
        self.assertEqual({path.name for path in iconset.iterdir()}, expected)
        self.assertEqual((iconset / 'icon_512x512@2x.png').read_bytes(), master.read_bytes(),
                         'The 1024px ICNS input must retain the Illustrator master without changes.')
        bundled = BUILD / 'bin/Alright.app/Contents/Resources/Alright.icns'
        generated = BUILD / 'generated/Alright.icns'
        self.assertEqual(hashlib.sha256(bundled.read_bytes()).digest(),
                         hashlib.sha256(generated.read_bytes()).digest())

    def test_single_self_contained_application(self):
        self.assertIn(CACHE['ALRIGHT_APP_STORE:BOOL'], ('ON', 'OFF'))
        app_store = CACHE['ALRIGHT_APP_STORE:BOOL'] == 'ON'
        app = BUILD / 'bin/Alright.app'
        self.assertEqual(list(BUILD.rglob('*.app')), [app])
        with (app / 'Contents/Info.plist').open('rb') as stream:
            info = plistlib.load(stream)
        self.assertEqual(info['CFBundleIdentifier'], 'com.iisacc.Alright')
        self.assertEqual(info['CFBundlePackageType'], 'APPL')
        self.assertEqual(info['CFBundleIconFile'], 'Alright.icns')
        self.assertEqual(info['CFBundleIcons']['CFBundlePrimaryIcon']['CFBundleSymbolName'], 'folder',
                         'Registered folders must use the folder SF Symbol in Finder rather than the app icon.')
        self.assertEqual(info['LSApplicationCategoryType'], 'public.app-category.utilities')
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
        self.assertEqual(plugin['CFBundleShortVersionString'], info['CFBundleShortVersionString'],
                         'The host and Finder extension must submit the same version.')
        self.assertEqual(plugin['CFBundleVersion'], info['CFBundleVersion'],
                         'The host and Finder extension must submit the same build number.')
        self.assertIs(plugin.get('LSUIElement'), True,
                      'The Finder Sync extension must declare LSUIElement as a boolean true for App Store validation.')
        subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(extension)], check=True)
        for binary in (executable, extension / 'Contents/MacOS/AlrightFinderSync'):
            build = subprocess.check_output(['/usr/bin/xcrun', 'vtool', '-show-build', str(binary)], text=True)
            self.assertIn('minos 14.0', build)
            symbols = subprocess.check_output(['/usr/bin/nm', str(binary)], text=True)
            self.assertIn('_swift_', symbols)
            self.assertEqual([p.name for p in binary.parent.iterdir()], [binary.name])
        groups = []
        teams = []
        for bundle in (app, extension):
            raw = subprocess.check_output(['/usr/bin/codesign', '-d', '--entitlements', ':-', str(bundle)], stderr=subprocess.DEVNULL)
            entitlements = plistlib.loads(raw)
            self.assertEqual(entitlements.get('com.apple.security.app-sandbox', False), app_store or bundle == extension)
            groups.append(entitlements['com.apple.security.application-groups'])
            signature = subprocess.check_output(['/usr/bin/codesign', '-d', '-vv', str(bundle)], text=True, stderr=subprocess.STDOUT)
            teams.append(next(line.removeprefix('TeamIdentifier=') for line in signature.splitlines() if line.startswith('TeamIdentifier=')))
            if app_store:
                self.assertTrue(any(line.startswith(('Authority=Apple Distribution:',
                                                      'Authority=3rd Party Mac Developer Application:'))
                                    for line in signature.splitlines()))
        self.assertEqual(groups[0], groups[1])
        self.assertEqual(teams, [CACHE['ALRIGHT_TEAM_ID:STRING']] * 2)
        self.assertEqual(groups[0], [f'{teams[0]}.com.iisacc.Alright'])


if __name__ == '__main__':
    unittest.main()
