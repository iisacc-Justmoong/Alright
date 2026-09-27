"""Package reviewed XML sources as deterministic blank Office documents (stdlib only)."""
import sys
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED

source, destination = map(Path, sys.argv[1:3])
destination.mkdir(parents=True, exist_ok=True)
for kind in ('docx', 'xlsx', 'pptx', 'odt', 'ods', 'odp'):
    folder = source / kind
    files = sorted(p for p in folder.rglob('*') if p.is_file())
    if kind.startswith('od'):
        files.remove(folder / 'mimetype')
        files.insert(0, folder / 'mimetype')
    target = destination / ('Blank.' + kind)
    with ZipFile(target, 'w') as archive:
        for file in files:
            name = file.relative_to(folder).as_posix()
            entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_STORED if name == 'mimetype' else ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, file.read_bytes())
