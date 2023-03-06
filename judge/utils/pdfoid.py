import base64
import logging

import requests
from django.conf import settings
from django.utils.translation import gettext

logger = logging.getLogger('judge.problem.pdf')


PDFOID_URL = settings.DMOJ_PDF_PDFOID_URL
PDF_RENDERING_ENABLED = PDFOID_URL is not None


def render_pdf(*, title: str, html: str, footer: bool = False) -> bytes:
    if not PDF_RENDERING_ENABLED:
        raise RuntimeError("pdfoid is not configured, can't render PDFs")

    if footer:
        footer_template = (
            '<center style="margin: 0 auto; font-family: Segoe UI; font-size: 10px">' +
            gettext('Page {page_number} of {total_pages}') +
            '</center>')
    else:
        footer_template = None

    response = requests.post(
        PDFOID_URL,
        data={
            'html': html,
            'title': title,
            'footer-template': footer_template,
            'wait-for-class': 'math-loaded',
            'wait-for-duration-secs': 15,
        },
    )

    response.raise_for_status()
    data = response.json()

    if not data['success']:
        raise RuntimeError(data['error'])

    return base64.b64decode(data['pdf'])
