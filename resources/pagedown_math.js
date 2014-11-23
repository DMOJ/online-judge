('$' in window ? $ : django.jQuery).ready(function ($) {
    if ('MathJax' in window) {
        $.each(window.editors, function (id, editor) {
            // var textarea = $('textarea.wmd-input#' + id);
            var preview = $('div.wmd-preview#' + id + '_wmd_preview')[0];
            editor.hooks.chain('onPreviewRefresh', function () {
                MathJax.Hub.Queue(["Typeset", MathJax.Hub, preview]);
            });
        });
    }
});
