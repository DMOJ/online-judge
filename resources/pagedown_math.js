function mathjax_pagedown($) {
    if ('MathJax' in window) {
        $.each(window.editors, function (id, editor) {
            var preview = $('div.wmd-preview#' + id + '_wmd_preview')[0];
            if (preview) {
                editor.hooks.chain('onPreviewRefresh', function () {
                    MathJax.typeset([preview]);
                });
                MathJax.typeset([preview]);
            }
        });
    }
}

window.mathjax_pagedown = mathjax_pagedown;

$(window).on('load', function () {
    (mathjax_pagedown)('$' in window ? $ : django.jQuery);
});
