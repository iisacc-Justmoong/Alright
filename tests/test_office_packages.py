"""Exercise the Swift creation path, then independently inspect package semantics."""
import posixpath
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED

BUILD = Path(sys.argv.pop(1)).resolve()
FORMATS = {'word': 'docx', 'excel': 'xlsx', 'powerpoint': 'pptx',
           'openDocumentText': 'odt', 'openDocumentSpreadsheet': 'ods', 'openDocumentPresentation': 'odp'}
NS = dict(w='http://schemas.openxmlformats.org/wordprocessingml/2006/main',
          s='http://schemas.openxmlformats.org/spreadsheetml/2006/main',
          p='http://schemas.openxmlformats.org/presentationml/2006/main',
          a='http://schemas.openxmlformats.org/drawingml/2006/main',
          office='urn:oasis:names:tc:opendocument:xmlns:office:1.0',
          text='urn:oasis:names:tc:opendocument:xmlns:text:1.0',
          table='urn:oasis:names:tc:opendocument:xmlns:table:1.0',
          draw='urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
          manifest='urn:oasis:names:tc:opendocument:xmlns:manifest:1.0')

class OfficePackages(unittest.TestCase):
    def test_created_office_documents(self):
        fixture_root = BUILD / 'fixtures'
        fixture_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=fixture_root) as tmp:
            for kind, extension in FORMATS.items():
                with self.subTest(extension=extension):
                    output = Path(tmp) / ('Blank.' + extension)
                    subprocess.run([str(BUILD / 'AlrightDocumentFixture'), kind, '5120', '2880',
                                    str(BUILD / 'bin/Alright.app/Contents/Resources/DocumentTemplates'), str(output)], check=True)
                    with ZipFile(output) as z:
                        self.assertIsNone(z.testzip(), 'all CRCs and entries valid')
                        self.assertEqual(len(z.namelist()), len(set(z.namelist())))
                        self.assertFalse(any('vba' in name.lower() for name in z.namelist()))
                        xml = {n: ET.fromstring(z.read(n)) for n in z.namelist() if n.endswith(('.xml', '.rels'))}
                        if extension.startswith('od'):
                            self.check_odf(z, xml, extension)
                        else:
                            self.check_ooxml(z, xml, extension)

    def check_ooxml(self, z, xml, extension):
        for name, document in xml.items():
            if name.endswith('.rels'):
                parent = '' if name == '_rels/.rels' else posixpath.dirname(posixpath.dirname(name))
                ids = [item.attrib['Id'] for item in document]
                self.assertEqual(len(ids), len(set(ids)))
                for relationship in document:
                    self.assertNotEqual(relationship.get('TargetMode'), 'External')
                    target = posixpath.normpath(posixpath.join(parent, relationship.attrib['Target']))
                    self.assertIn(target, z.namelist(), name)
        types = xml['[Content_Types].xml']
        overrides = {x.attrib['PartName'].lstrip('/'): x.attrib['ContentType'] for x in types if x.tag.endswith('Override')}
        for path in z.namelist():
            if path.endswith('.xml') and path != '[Content_Types].xml':
                self.assertIn(path, overrides, 'specific content type for each document part')
        if extension == 'docx':
            doc = xml['word/document.xml']
            self.assertEqual(len(doc.findall('.//w:body/w:p', NS)), 1)
            self.assertFalse(doc.findall('.//w:t', NS), 'blank body')
            self.assertIsNotNone(doc.find('.//w:sectPr/w:pgSz', NS))
        elif extension == 'xlsx':
            self.assertEqual(len(xml['xl/workbook.xml'].findall('.//s:sheet', NS)), 1)
            self.assertFalse(xml['xl/worksheets/sheet1.xml'].findall('.//s:c', NS), 'no populated cells')
            self.assertEqual(xml['xl/worksheets/sheet1.xml'].find('.//s:selection', NS).get('activeCell'), 'A1')
        else:
            doc = xml['ppt/presentation.xml']
            self.assertEqual(len(doc.findall('.//p:sldId', NS)), 1)
            self.assertIsNotNone(doc.find('.//p:sldMasterId', NS))
            self.assertEqual(doc.find('p:sldSz', NS).get('cx'), '12192000')
            self.assertFalse(xml['ppt/slides/slide1.xml'].findall('.//p:sp', NS), 'blank slide')
            self.assertIsNotNone(xml['ppt/theme/theme1.xml'].find('a:themeElements', NS))
            self.assertEqual(xml['ppt/slideLayouts/slideLayout1.xml'].get('type'), 'blank')

    def check_odf(self, z, xml, extension):
        typ = {'odt': 'text', 'ods': 'spreadsheet', 'odp': 'presentation'}[extension]
        mime = 'application/vnd.oasis.opendocument.' + typ
        self.assertEqual(z.infolist()[0].filename, 'mimetype')
        self.assertEqual(z.infolist()[0].compress_type, ZIP_STORED)
        self.assertEqual(z.infolist()[0].extra, b'')
        self.assertEqual(z.read('mimetype').decode(), mime)
        entries = xml['META-INF/manifest.xml']
        paths = {x.get('{'+NS['manifest']+'}full-path'): x.get('{'+NS['manifest']+'}media-type') for x in entries}
        self.assertEqual(paths['/'], mime)
        self.assertEqual(set(paths), {'/', 'content.xml', 'styles.xml'})
        doc = xml['content.xml']
        self.assertIsNotNone(doc.find('office:body/office:'+typ, NS))
        if extension == 'odt':
            self.assertEqual(len(doc.findall('.//text:p', NS)), 1)
            self.assertFalse(''.join(doc.itertext()).strip())
        elif extension == 'ods':
            self.assertEqual(len(doc.findall('.//table:table', NS)), 1)
            self.assertEqual(len(doc.findall('.//table:table-cell', NS)), 1)
            self.assertFalse(''.join(doc.itertext()).strip())
        else:
            self.assertEqual(len(doc.findall('.//draw:page', NS)), 1)
            self.assertEqual(len(doc.find('.//draw:page', NS)), 0)

if __name__ == '__main__':
    unittest.main()
