import errno
import io
import os
import shutil
import subprocess
import tempfile
import uuid

from django.conf import settings

HAS_PDF = (os.path.isdir(getattr(settings, 'PROBLEM_PDF_CACHE', '')) and
           os.access(getattr(settings, 'WKHTMLTOPDF', ''), os.X_OK))


class WebKitPdfMaker(object):
    def __init__(self, dir=None, clean_up=True):
        self.dir = dir or os.path.join(getattr(settings, 'WKHTMLTOPDF_TEMP_DIR', tempfile.gettempdir()), str(uuid.uuid1()))
        self.proc = None
        self.log = None
        self.htmlfile = os.path.join(self.dir, 'input.html')
        self.pdffile = os.path.join(self.dir, 'output.pdf')
        self.clean_up = clean_up

    def make(self, debug=False):
        command = [
            getattr(settings, 'WKHTMLTOPDF', 'wkhtmltopdf'), '--enable-javascript', '--javascript-delay', '5000',
            '--footer-center', 'Page [page] of [topage]', '--footer-font-name', 'Segoe UI',
            '--footer-font-size', '10', '--encoding', 'utf-8',
            'input.html', 'output.pdf'
        ]
        if debug:
            print subprocess.list2cmdline(command)
        self.proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.dir)
        self.log = self.proc.communicate()[0]

    def load(self, file, source):
        with open(os.path.join(self.dir, file), 'w') as target, open(source) as source:
            target.write(source.read())

    @property
    def html(self):
        with io.open(self.htmlfile, encoding='utf-8') as f:
            return f.read()

    @html.setter
    def html(self, data):
        with io.open(self.htmlfile, 'w', encoding='utf-8') as f:
            f.write(data)

    @property
    def success(self):
        return self.proc.returncode == 0

    @property
    def created(self):
        return os.path.exists(self.pdffile)

    def __enter__(self):
        try:
            os.makedirs(self.dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.clean_up:
            shutil.rmtree(self.dir, ignore_errors=True)
