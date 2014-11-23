(function ($) {
    if ('MathJax' in window) {
        $(window).load(function () {
            $.each(window.editors, function (id, editor) {
                var preview = $('div.wmd-preview#' + id + '_wmd_preview')[0];
                editor.hooks.chain('onPreviewRefresh', function () {
                    MathJax.Hub.Queue(["Typeset", MathJax.Hub, preview]);
                });
            });
        });
    }
})('$' in window ? $ : django.jQuery);