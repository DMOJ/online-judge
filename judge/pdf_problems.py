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
from judge.math_parser import MathHTMLParser

from markdown_trois import markdown as markdown_trois


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
\usepackage{longtable}
\usepackage{tabu}
\usepackage{tabulary}
\usepackage[export]{adjustbox}

\setlength{\parskip}{1em}
\renewcommand{\arraystretch}{1.5}

\usepackage[newcommands]{ragged2e}

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

\setlength{\parindent}{0pt}

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

retable = re.compile(r'(?<=\\begin\{longtable\}\[c\]\{@\{\})l+(?=@\{\}\})')
retablebegin = re.compile(r'\\begin\{longtable\}\[c\]\{@\{\}l+@\{\}\}')
remath = re.compile(r'(?<=\\\().+?(?=\\\))')
redisplaymath = re.compile(r'(?<=\\\[).+?(?=\\\])')


class DollarMath(MathHTMLParser):
    def inline_math(self, math):
        return r'\\(%s\\)' % math

    def display_math(self, math):
        return r'\\[%s\\]' % math


def format_markdown(markdown):
    return DollarMath.convert(markdown)


def make_latex(markdown, style='problem'):
    html = markdown_trois(markdown, style)
    pandoc = getattr(settings, 'PANDOC_PATH', None)
    if isinstance(html, unicode):
        html = html.encode('utf-8')
    if pandoc is not None:
        proc = subprocess.Popen([pandoc, '-f', 'html', '-t', 'latex'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        return proc.communicate(html)[0].decode('utf-8')
    else:
        # Sorry, but can't install haskell on openshift.
        stream = urllib2.urlopen('http://johnmacfarlane.net/cgi-bin/trypandoc?%s' % urllib.urlencode({
            'from': 'html', 'to': 'latex', 'text': html
        }))
        result = json.load(stream)
        stream.close()
        return result['result']


def wget_graphics(match):
    path = match.group(1)
    return r'''
\begin{center}
    \immediate\write18{wget %s}
    \includegraphics[max width=\textwidth]{%s}
\end{center}
''' % (path, path[path.rfind('/') + 1:])


def latex_document(title, author, fragment):
    latex = fragment.replace('\subsection{', '\section{')
    for a, b in LATEX_REPLACE:
        latex = latex.replace(a, b)
    latex = refilename.sub(wget_graphics, latex)
    latex = latex.replace(r'\begin{Highlighting}[]', r'\begin{Highlighting}')
    latex = latex.replace(r'\textbackslash{}(', r'\(')
    latex = latex.replace(r'\textbackslash{})', r'\)')
    latex = latex.replace(r'\textbackslash{}le', r'\le')
    latex = latex.replace(r'\textbackslash{}ge', r'\ge')
    latex = latex.replace(r'\textbackslash{}ne', r'\ne')
    latex = latex.replace(r'\paragraph{', r'\section{')
    latex = remath.sub(lambda m: m.group(0).replace(r'\textbackslash{}', '\\'), latex)
    latex = redisplaymath.sub(lambda m: m.group(0).replace(r'\textbackslash{}', '\\'), latex)
    latex = retablebegin.sub(lambda m: r'%s\hline' % m.group(0), latex)
    latex = retable.sub(lambda m: '| %s |' % ' | '.join(['l' for l in m.group(0)[:-1]]+['X']), latex)
    latex = latex.replace(r'\tabularnewline', r'\\ \hline')
    latex = latex.replace(r'\begin{longtable}[c]', r'\begin{tabu} to \textwidth ')
    latex = latex.replace(r'\end{longtable}', r'\end{tabu}')
    # FIXME
    latex = latex.replace(r'{@{}', r'{')
    latex = latex.replace(r'@{}}', r'}')
    for f in [r'\toprule', r'\midrule', r'\endhead', r'\bottomrule']:
        latex = latex.replace(f, '')
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


class WebKitPdfMaker(object):
    def __init__(self):
        self.dir = os.path.join(getattr(settings, 'WKHTMLTOPDF_TEMP_DIR', tempfile.gettempdir()), str(uuid.uuid1()))
        self.proc = None
        self.log = None
        self.htmlfile = os.path.join(self.dir, 'input.html')
        self.pdffile = os.path.join(self.dir, 'output.pdf')

    def make(self):
        self.proc = subprocess.Popen([
            getattr(settings, 'WKHTMLTOPDF', 'wkhtmltopdf'), '--enable-javascript', '--javascript-delay', '5000',
            'input.html', '--footer-center', '[page]/[topage]', 'output.pdf'
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.dir)
        self.log = self.proc.communicate()[0]

    def load(self, file, source):
        with open(os.path.join(self.dir, file), 'w') as target, open(source) as source:
            target.write(source.read())

    @property
    def html(self):
        with open(self.htmlfile) as f:
            return f.read()

    @html.setter
    def html(self, data):
        with open(self.htmlfile, 'w') as f:
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
