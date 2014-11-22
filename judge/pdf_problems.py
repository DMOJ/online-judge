import os
import uuid
import errno
import urllib2
import urllib
import json
import shutil
import subprocess
import tempfile
import re

from django.conf import settings


refilename = re.compile(r'\\includegraphics{(.*?)}')
PROLOGUE = r'''\documentclass[a4paper]{article}

\usepackage{fullpage}
\usepackage[english]{babel}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{hyperref}
\usepackage{bookmark}
\usepackage[pdftex]{graphicx}
\usepackage{amssymb}

\usepackage[utf8]{inputenc}

\usepackage{color}
\usepackage{fancyvrb}

\newenvironment{Highlighting}
    {
        \VerbatimEnvironment
        \begin{Verbatim}[commandchars=\\\{\}]%%
    }
    {\end{Verbatim}}
\newenvironment{Shaded}{}{}
\newcommand{\KeywordTok}[1]{\textcolor[rgb]{0.00,0.00,0.00}{\textbf{{#1}}}}
\newcommand{\DataTypeTok}[1]{\textcolor[rgb]{0.25,0.31,0.50}{\textbf{{#1}}}}
\newcommand{\DecValTok}[1]{\textcolor[rgb]{0.00,0.56,0.56}{{#1}}}
\newcommand{\BaseNTok}[1]{\textcolor[rgb]{0.00,0.56,0.56}{{#1}}}
\newcommand{\FloatTok}[1]{\textcolor[rgb]{0.00,0.56,0.56}{{#1}}}
\newcommand{\CharTok}[1]{\textcolor[rgb]{0.82,0.06,0.25}{{#1}}}
\newcommand{\StringTok}[1]{\textcolor[rgb]{0.82,0.06,0.25}{{#1}}}
\newcommand{\CommentTok}[1]{\textcolor[rgb]{0.56,0.56,0.50}{\textit{{#1}}}}
\newcommand{\OtherTok}[1]{\textcolor[rgb]{0.00,0.44,0.13}{{#1}}}
\newcommand{\AlertTok}[1]{\textcolor[rgb]{1.00,0.00,0.00}{\textbf{{#1}}}}
\newcommand{\FunctionTok}[1]{\textcolor[rgb]{0.56,0.00,0.00}{{#1}}}
\newcommand{\RegionMarkerTok}[1]{{#1}}
\newcommand{\ErrorTok}[1]{\textcolor[rgb]{1.00,0.00,0.00}{\textbf{{#1}}}}
\newcommand{\NormalTok}[1]{{#1}}



\title{\%s \bf %s}
\author{%s}
\date{\vspace{-5ex}}

\makeatletter
\renewcommand\@seccntformat[1]{\large}
\makeatother

\begin{document}
\maketitle
'''

# \usepackage{listings}

EPILOGUE = r'''
\end{document}'''

LATEX_REPLACE = [
    (u'\u2190', r'\(\leftarrow\)'),
    (u'\u2192', r'\(\rightarrow\)'),
    (u'\u2264', r'\le'),
    (u'\u2265', r'\ge'),
    (u'\u2026', '...'),
    (u'\u2212', '-'),
    ('&le;', r'\le'),
    ('&le;', r'\ge'),
    (r'\lt', '<'),
    (r'\gt', '>'),
]


def format_markdown(markdown):
    return markdown.replace('~', '$').replace(r'\\(', '$').replace(r'\\)', '$').replace(r'\_', '_')

def pandoc_do(source, to, text):
    stream = urllib2.urlopen('http://johnmacfarlane.net/cgi-bin/trypandoc?%s' % urllib.urlencode({
        'from': source, 'to': to, 'text': text
    }))
    result = json.load(stream)
    stream.close()
    return result['result']


def make_latex(markdown):
    pandoc = getattr(settings, 'PANDOC_PATH', None)
    if pandoc is not None:
        proc = subprocess.Popen([pandoc, '-f', 'markdown', '-t', 'latex'], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
        return proc.communicate(markdown)[0]
    else:
        # Sorry, but can't install haskell on openshift.
        if isinstance(markdown, unicode):
            markdown = markdown.encode('utf-8')
        # This double conversion allows for tables
        html = pandoc_do('markdown_github', 'html', markdown).encode('utf-8')
        return pandoc_do('html', 'latex', html)


def wget_graphics(match):
    path = match.group(1)
    return r'''\immediate\write18{wget %s}
\includegraphics{%s}
''' % (path, path[path.rfind('/') + 1:])


def latex_document(title, author, fragment):
    latex = fragment.replace('\subsection{', '\section{')
    for a, b in LATEX_REPLACE:
        latex = latex.replace(a, b)
    latex = refilename.sub(wget_graphics, latex)
    latex = latex.replace(r'\begin{Highlighting}[]', r'\begin{Highlighting}')
    return PROLOGUE % (['Huge', 'LARGE'][len(title) > 30], title.replace('#', r'\#'), author) + latex + EPILOGUE


class LatexPdfMaker(object):
    def __init__(self, source):
        self.dir = os.path.join(getattr(settings, 'PDFLATEX_TEMP_DIR', tempfile.gettempdir()), str(uuid.uuid1()))
        self.proc = None
        self.log = None
        self.source = source
        self.texfile = os.path.join(self.dir, 'output.tex')
        self.pdffile = os.path.join(self.dir, 'output.pdf')

        if isinstance(source, unicode):
            self.source = source.encode('utf-8')

    def make(self):
        with open(self.texfile, 'wb') as f:
            f.write(self.source)
        self.proc = subprocess.Popen([
            getattr(settings, 'PDFLATEX_PATH', 'pdflatex'), '--shell-escape',
            '-interaction', 'nonstopmode',
            '-file-line-error', 'output.tex'
        ], stdout=subprocess.PIPE, cwd=self.dir)
        self.log = self.proc.communicate()[0]

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
        shutil.rmtree(self.dir, ignore_errors=True)


def main():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='Make a pdf from DMOJ problem.')
    parser.add_argument('title')
    parser.add_argument('author')
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'),
                        default=sys.stdin)
    parser.add_argument('outfile', nargs='?', default='-')

    args = parser.parse_args()
    fragment = make_latex(format_markdown(args.infile.read()))
    document = latex_document(args.title, args.author, fragment)
    with LatexPdfMaker(document) as latex:
        latex.make()
        if latex.success:
            if args.outfile == '-':
                sys.stdout.write(open(latex.pdffile, 'rb').read())
            else:
                os.rename(latex.pdffile, args.outfile)
        else:
            print latex.log


if __name__ == '__main__':
    main()
