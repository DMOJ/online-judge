import base64
import errno
import io
import json
import logging
import os
import shutil
import subprocess
import uuid

from django.conf import settings
from django.utils.translation import gettext

logger = logging.getLogger('judge.problem.pdf')

HAS_SELENIUM = False
if settings.USE_SELENIUM:
    try:
        from selenium import webdriver
        from selenium.common.exceptions import TimeoutException
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
        HAS_SELENIUM = True
    except ImportError:
        logger.warning('Failed to import Selenium', exc_info=True)

HAS_PHANTOMJS = os.access(settings.PHANTOMJS, os.X_OK)
HAS_SLIMERJS = os.access(settings.SLIMERJS, os.X_OK)

NODE_PATH = settings.NODEJS
PUPPETEER_MODULE = settings.PUPPETEER_MODULE
HAS_PUPPETEER = os.access(NODE_PATH, os.X_OK) and os.path.isdir(PUPPETEER_MODULE)

HAS_PDF = (os.path.isdir(settings.DMOJ_PDF_PROBLEM_CACHE) and
           (HAS_PHANTOMJS or HAS_SLIMERJS or HAS_PUPPETEER or HAS_SELENIUM))

EXIFTOOL = settings.EXIFTOOL
HAS_EXIFTOOL = os.access(EXIFTOOL, os.X_OK)


class BasePdfMaker(object):
    math_engine = 'jax'
    title = None

    def __init__(self, dir=None, clean_up=True):
        self.dir = dir or os.path.join(settings.DMOJ_PDF_PROBLEM_TEMP_DIR, str(uuid.uuid1()))
        self.proc = None
        self.log = None
        self.htmlfile = os.path.join(self.dir, 'input.html')
        self.pdffile = os.path.join(self.dir, 'output.pdf')
        self.clean_up = clean_up

    def load(self, file, source):
        with open(os.path.join(self.dir, file), 'w') as target, open(source) as source:
            target.write(source.read())

    def make(self, debug=False):
        self._make(debug)

        if self.title and HAS_EXIFTOOL:
            try:
                subprocess.check_output([EXIFTOOL, '-Title=%s' % (self.title,), self.pdffile])
            except subprocess.CalledProcessError as e:
                logger.error('Failed to run exiftool to set title for: %s\n%s', self.title, e.output)

    def _make(self, debug):
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


class PhantomJSPdfMaker(BasePdfMaker):
    template = '''\
"use strict";
var page = require('webpage').create();
var param = {params};

page.paperSize = {
    format: param.paper, orientation: 'portrait', margin: '1cm',
    footer: {
        height: '1cm',
        contents: phantom.callback(function(num, pages) {
            return ('<center style="margin: 0 auto; font-family: Segoe UI; font-size: 10px">'
                  + param.footer.replace('[page]', num).replace('[topage]', pages) + '</center>');
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
        page.evaluate(function (zoom) {
            document.documentElement.style.zoom = zoom;
        }, param.zoom);
        window.setTimeout(function () {
            page.render(param.output);
            phantom.exit();
        }, param.timeout);
    }
});
'''

    def get_render_script(self):
        return self.template.replace('{params}', json.dumps({
            'zoom': settings.PHANTOMJS_PDF_ZOOM,
            'timeout': int(settings.PHANTOMJS_PDF_TIMEOUT * 1000),
            'input': 'input.html', 'output': 'output.pdf',
            'paper': settings.PHANTOMJS_PAPER_SIZE,
            'footer': gettext('Page [page] of [topage]'),
        }))

    def _make(self, debug):
        with io.open(os.path.join(self.dir, '_render.js'), 'w', encoding='utf-8') as f:
            f.write(self.get_render_script())
        cmdline = [settings.PHANTOMJS, '_render.js']
        env = {'OPENSSL_CONF': '/etc/ssl'}
        self.proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.dir, env=env)
        self.log = self.proc.communicate()[0]


class SlimerJSPdfMaker(BasePdfMaker):
    math_engine = 'mml'

    template = '''\
"use strict";
try {
    var param = {params};

    var {Cc, Ci} = require('chrome');
    var prefs = Cc['@mozilla.org/preferences-service;1'].getService(Ci.nsIPrefService);
    // Changing the serif font so that printed footers show up as Segoe UI.
    var branch = prefs.getBranch('font.name.serif.');
    branch.setCharPref('x-western', 'Segoe UI');

    var page = require('webpage').create();

    page.paperSize = {
        format: param.paper, orientation: 'portrait', margin: '1cm', edge: '0.5cm',
        footerStr: { left: '', right: '', center: param.footer }
    };

    page.open(param.input, function (status) {
        if (status !== 'success') {
            console.log('Unable to load the address!');
            slimer.exit(1);
        } else {
            page.render(param.output, { ratio: param.zoom });
            slimer.exit();
        }
    });
} catch (e) {
    console.error(e);
    slimer.exit(1);
}
'''

    def get_render_script(self):
        return self.template.replace('{params}', json.dumps({
            'zoom': settings.SLIMERJS_PDF_ZOOM,
            'input': 'input.html', 'output': 'output.pdf',
            'paper': settings.SLIMERJS_PAPER_SIZE,
            'footer': gettext('Page [page] of [topage]').replace('[page]', '&P').replace('[topage]', '&L'),
        }))

    def _make(self, debug):
        with io.open(os.path.join(self.dir, '_render.js'), 'w', encoding='utf-8') as f:
            f.write(self.get_render_script())

        env = None
        firefox = settings.SLIMERJS_FIREFOX_PATH
        if firefox:
            env = os.environ.copy()
            env['SLIMERJSLAUNCHER'] = firefox

        cmdline = [settings.SLIMERJS, '--headless', '_render.js']
        self.proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.dir, env=env)
        self.log = self.proc.communicate()[0]


class PuppeteerPDFRender(BasePdfMaker):
    template = '''\
"use strict";
const param = {params};
const puppeteer = require('puppeteer');

puppeteer.launch().then(browser => Promise.resolve()
    .then(async () => {
        const page = await browser.newPage();
        await page.goto(param.input, { waitUntil: 'load' });
        await page.waitForSelector('.math-loaded', { timeout: 15000 });
        await page.pdf({
            path: param.output,
            format: param.paper,
            margin: {
                top: '1cm',
                bottom: '1cm',
                left: '1cm',
                right: '1cm',
            },
            printBackground: true,
            displayHeaderFooter: true,
            headerTemplate: '<div></div>',
            footerTemplate: '<center style="margin: 0 auto; font-family: Segoe UI; font-size: 10px">' +
                param.footer.replace('[page]', '<span class="pageNumber"></span>')
                            .replace('[topage]', '<span class="totalPages"></span>')
                + '</center>',
        });
        await browser.close();
    })
    .catch(e => browser.close().then(() => {throw e}))
).catch(e => {
    console.error(e);
    process.exit(1);
});
'''

    def get_render_script(self):
        return self.template.replace('{params}', json.dumps({
            'input': 'file://%s' % self.htmlfile,
            'output': self.pdffile,
            'paper': settings.PUPPETEER_PAPER_SIZE,
            'footer': gettext('Page [page] of [topage]'),
        }))

    def _make(self, debug):
        with io.open(os.path.join(self.dir, '_render.js'), 'w', encoding='utf-8') as f:
            f.write(self.get_render_script())

        env = os.environ.copy()
        env['NODE_PATH'] = os.path.dirname(PUPPETEER_MODULE)

        cmdline = [NODE_PATH, '_render.js']
        self.proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.dir, env=env)
        self.log = self.proc.communicate()[0]


class SeleniumPDFRender(BasePdfMaker):
    success = False
    template = {
        'printBackground': True,
        'displayHeaderFooter': True,
        'headerTemplate': '<div></div>',
        'footerTemplate': '<center style="margin: 0 auto; font-family: Segoe UI; font-size: 10px">' +
                          gettext('Page %s of %s') %
                          ('<span class="pageNumber"></span>', '<span class="totalPages"></span>') +
                          '</center>',
    }

    def get_log(self, driver):
        return '\n'.join(map(str, driver.get_log('driver') + driver.get_log('browser')))

    def _make(self, debug):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.binary_location = settings.SELENIUM_CUSTOM_CHROME_PATH

        browser = webdriver.Chrome(settings.SELENIUM_CHROMEDRIVER_PATH, options=options)
        browser.get('file://%s' % self.htmlfile)
        self.log = self.get_log(browser)

        try:
            WebDriverWait(browser, 15).until(EC.presence_of_element_located((By.CLASS_NAME, 'math-loaded')))
        except TimeoutException:
            logger.error('PDF math rendering timed out')
            self.log = self.get_log(browser) + '\nPDF math rendering timed out'
            return

        response = browser.execute_cdp_cmd('Page.printToPDF', self.template)
        self.log = self.get_log(browser)
        if not response:
            return

        with open(self.pdffile, 'wb') as f:
            f.write(base64.b64decode(response['data']))

        self.success = True


if HAS_PUPPETEER:
    DefaultPdfMaker = PuppeteerPDFRender
elif HAS_SELENIUM:
    DefaultPdfMaker = SeleniumPDFRender
elif HAS_SLIMERJS:
    DefaultPdfMaker = SlimerJSPdfMaker
elif HAS_PHANTOMJS:
    DefaultPdfMaker = PhantomJSPdfMaker
else:
    DefaultPdfMaker = None
