import errno
import io
import json
import os
import shutil
import subprocess
import tempfile
import uuid

from django.conf import settings
from django.utils.translation import ugettext

HAS_PHANTOMJS = os.access(getattr(settings, 'PHANTOMJS', ''), os.X_OK)
HAS_WKHTMLTOPDF = os.access(getattr(settings, 'WKHTMLTOPDF', ''), os.X_OK)
HAS_PDF = (os.path.isdir(getattr(settings, 'PROBLEM_PDF_CACHE', '')) and
           (HAS_PHANTOMJS or HAS_WKHTMLTOPDF))


class BasePdfMaker(object):
    def __init__(self, dir=None, clean_up=True):
        self.dir = dir or os.path.join(getattr(settings, 'PROBLEM_PDF_TEMP_DIR', tempfile.gettempdir()), str(uuid.uuid1()))
        self.proc = None
        self.log = None
        self.htmlfile = os.path.join(self.dir, 'input.html')
        self.pdffile = os.path.join(self.dir, 'output.pdf')
        self.clean_up = clean_up

    def load(self, file, source):
        with open(os.path.join(self.dir, file), 'w') as target, open(source) as source:
            target.write(source.read())

    def make(self, debug=False):
        raise NotImplementedError()

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


class WebKitPdfMaker(BasePdfMaker):
    def make(self, debug=False):
        command = [
            getattr(settings, 'WKHTMLTOPDF', 'wkhtmltopdf'), '--enable-javascript', '--javascript-delay', '5000',
            '--footer-center', ugettext('Page [page] of [topage]').encode('utf-8'), '--footer-font-name', 'Segoe UI',
            '--footer-font-size', '10', '--encoding', 'utf-8',
            'input.html', 'output.pdf'
        ]
        if debug:
            print subprocess.list2cmdline(command)
        self.proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.dir)
        self.log = self.proc.communicate()[0]


class PhantomJSPdfMaker(BasePdfMaker):
    template = u'''
"use strict";
var page = require('webpage').create();
var param = {params};

page.paperSize = {
    format: param.paper, orientation: 'portrait', margin: '1cm',
    footer: {
        height: '1cm',
        contents: phantom.callback(function(num, pages) {
            return ('<center style="margin: 0 auto; font-family: Segoe UI; font-size: 10px">'
                  + param.footer + '</center>'.replace('[page]', num).replace('[topage]', pages));
        })
    }
};

page.onCallback = function (data) {
    if (data.action === 'snapshot') {
        page.render(param.output);
        phantom.exit();
    }
}

page.open(param.input, function (status) {
    if (status !== 'success') {
        console.log('Unable to load the address!');
        phantom.exit(1);
    } else {
        page.evaluate(function () {
            document.documentElement.style.zoom = param.zoom;
        });
        window.setTimeout(function () {
            page.render(output);
            phantom.exit();
        }, param.timeout);
    }
});
'''

    def get_render_script(self):
        return self.template.replace('{params}', json.dumps({
            'zoom': getattr(settings, 'PHANTOMJS_PDF_ZOOM', 0.75),
            'timeout': int(getattr(settings, 'PHANTOMJS_PDF_ZOOM', 10.0) * 1000),
            'input': 'input.html', 'output': 'output.pdf',
            'paper': getattr(settings, 'PHANTOMJS_PAPER_SIZE', 'Letter'),
            'footer': ugettext('Page [page] of [topage]').encode('utf-8'),
        }))

    def make(self, debug=False):
        with io.open(os.path.join(self.dir, '_render.js'), 'w', encoding='utf-8') as f:
            f.write(self.get_render_script())
        cmdline = [getattr(settings, 'PHANTOMJS', 'phantomjs'), '_render.js']
        self.proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.dir)
        self.log = self.proc.communicate()[0]

if HAS_PHANTOMJS:
    DefaultPdfMaker = PhantomJSPdfMaker
elif HAS_WKHTMLTOPDF:
    DefaultPdfMaker = WebKitPdfMaker
else:
    DefaultPdfMaker = None
