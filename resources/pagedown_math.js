function mathjax_pagedown($) {
    if ('MathJax' in window) {
        $.each(window.editors, function (id, editor) {
            var preview = $('div.wmd-preview#' + id + '_wmd_preview')[0];
            editor.hooks.chain('onPreviewRefresh', function () {
                MathJax.Hub.Queue(["Typeset", MathJax.Hub, preview]);
            });
            MathJax.Hub.Queue(["Typeset", MathJax.Hub, preview]);
        });
    }
}

window.mathjax_pagedown = mathjax_pagedown;

$(window).load(function () {
    (mathjax_pagedown)('$' in window ? $ : django.jQuery);
});