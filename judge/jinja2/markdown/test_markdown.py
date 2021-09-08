from django.test import SimpleTestCase
from lxml import html

from . import fragment_tree_to_str, fragments_to_tree, get_cleaner, markdown

MATHML_N = """\
<math xmlns="http://www.w3.org/1998/Math/MathML">
<semantics>
<mi>N</mi>
<annotation encoding="application/x-tex">N</annotation>
</semantics>
</math>
"""

MATHML_CHUDNOVSKY = r"""
<math xmlns="http://www.w3.org/1998/Math/MathML"
      alttext="{\displaystyle {\frac {1}{\pi }}=12\sum _{k=0}^{\infty }{\frac {(-1)^{k}(6k)!(545140134k+13591409)}{(3k)!(k!)^{3}\left(640320\right)^{3k+3/2}}}}">
  <semantics>
    <mrow class="MJX-TeXAtom-ORD">
      <mstyle displaystyle="true" scriptlevel="0">
        <mrow class="MJX-TeXAtom-ORD">
          <mfrac>
            <mn>1</mn>
            <mi>π<!-- π --></mi>
          </mfrac>
        </mrow>
        <mo>=</mo>
        <mn>12</mn>
        <munderover>
          <mo>∑<!-- ∑ --></mo>
          <mrow class="MJX-TeXAtom-ORD">
            <mi>k</mi>
            <mo>=</mo>
            <mn>0</mn>
          </mrow>
          <mrow class="MJX-TeXAtom-ORD">
            <mi mathvariant="normal">∞<!-- ∞ --></mi>
          </mrow>
        </munderover>
        <mrow class="MJX-TeXAtom-ORD">
          <mfrac>
            <mrow>
              <mo stretchy="false">(</mo>
              <mo>−<!-- − --></mo>
              <mn>1</mn>
              <msup>
                <mo stretchy="false">)</mo>
                <mrow class="MJX-TeXAtom-ORD">
                  <mi>k</mi>
                </mrow>
              </msup>
              <mo stretchy="false">(</mo>
              <mn>6</mn>
              <mi>k</mi>
              <mo stretchy="false">)</mo>
              <mo>!</mo>
              <mo stretchy="false">(</mo>
              <mn>545140134</mn>
              <mi>k</mi>
              <mo>+</mo>
              <mn>13591409</mn>
              <mo stretchy="false">)</mo>
            </mrow>
            <mrow>
              <mo stretchy="false">(</mo>
              <mn>3</mn>
              <mi>k</mi>
              <mo stretchy="false">)</mo>
              <mo>!</mo>
              <mo stretchy="false">(</mo>
              <mi>k</mi>
              <mo>!</mo>
              <msup>
                <mo stretchy="false">)</mo>
                <mrow class="MJX-TeXAtom-ORD">
                  <mn>3</mn>
                </mrow>
              </msup>
              <msup>
                <mrow>
                  <mo>(</mo>
                  <mn>640320</mn>
                  <mo>)</mo>
                </mrow>
                <mrow class="MJX-TeXAtom-ORD">
                  <mn>3</mn>
                  <mi>k</mi>
                  <mo>+</mo>
                  <mn>3</mn>
                  <mrow class="MJX-TeXAtom-ORD">
                    <mo>/</mo>
                  </mrow>
                  <mn>2</mn>
                </mrow>
              </msup>
            </mrow>
          </mfrac>
        </mrow>
      </mstyle>
    </mrow>
    <annotation encoding="application/x-tex">{\displaystyle {\frac {1}{\pi }}=12\sum _{k=0}^{\infty }{\frac {(-1)^{k}(6k)!(545140134k+13591409)}{(3k)!(k!)^{3}\left(640320\right)^{3k+3/2}}}}</annotation>
  </semantics>
</math>
"""  # noqa: E501


class TestMarkdown(SimpleTestCase):
    BLEACHED_STYLE = 'problem'
    UNBLEACHED_STYLE = 'problem-full'

    def test_bleach(self):
        self.assertHTMLEqual(markdown('<script>void(0)</script>', self.BLEACHED_STYLE),
                             '&lt;script&gt;void(0)&lt;/script&gt;')
        self.assertHTMLEqual(markdown('<img style="display: block; margin: 0 auto">', self.BLEACHED_STYLE),
                             '<p><img style="display: block; margin: 0 auto;"></p>')
        self.assertHTMLEqual(markdown('<style>a { color: red; }</style>', self.BLEACHED_STYLE),
                             '<style>a { color: red; }</style>')

    def test_bleach_mathml(self):
        self.assertHTMLEqual(markdown(MATHML_N, self.BLEACHED_STYLE), MATHML_N)
        cleaner = get_cleaner(self.BLEACHED_STYLE, None)
        self.assertHTMLEqual(cleaner.clean(MATHML_CHUDNOVSKY), MATHML_CHUDNOVSKY)

    def test_no_bleach(self):
        self.assertHTMLEqual(markdown('<script>void(0)</script>', self.UNBLEACHED_STYLE),
                             '<script>void(0)</script>')

    def test_post_process(self):
        self.assertHTMLEqual(markdown('<img src="test.png">', self.UNBLEACHED_STYLE, lazy_load=True),
                             '<p><noscript><img src="test.png"></noscript>'
                             '<img src="/static/blank.gif" data-src="test.png" class="unveil"></p>')


class TestFragmentUtils(SimpleTestCase):
    def test_simple(self):
        tree = fragments_to_tree('<p>a</p><p>b</p>')
        self.assertIsInstance(tree, html.HtmlElement)
        self.assertEqual(len(tree.getchildren()), 2)

        self.assertIsInstance(tree[0], html.HtmlElement)
        self.assertEqual(tree[0].tag, 'p')
        self.assertEqual(tree[0].text, 'a')

        self.assertIsInstance(tree[1], html.HtmlElement)
        self.assertEqual(tree[1].tag, 'p')
        self.assertEqual(tree[1].text, 'b')

        self.assertHTMLEqual(fragment_tree_to_str(tree), '<p>a</p><p>b</p>')

    def test_text_prefix(self):
        tree = fragments_to_tree('z<p>a</p><p>b</p>')
        self.assertIsInstance(tree, html.HtmlElement)
        self.assertEqual(len(tree.getchildren()), 2)
        self.assertEqual(tree.text, 'z')

        self.assertHTMLEqual(fragment_tree_to_str(tree), 'z<p>a</p><p>b</p>')
