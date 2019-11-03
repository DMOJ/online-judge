jQuery(function ($) {
    $(document).on('martor:preview', function (e, $content) {
        var $jax = $content.find('.require-mathjax-support');
        if ($jax.length) {
            if (!('MathJax' in window)) {
                $.ajax({
                    type: 'GET',
                    url: $jax.attr('data-config'),
                    dataType: 'script',
                    cache: true,
                    success: function () {
                        $.ajax({
                            type: 'GET',
                            url: 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-AMS_HTML',
                            dataType: 'script',
                            cache: true,
                            success: function () {
                                MathJax.Hub.Queue(function () {
                                    $content.find('.tex-image').hide();
                                    $content.find('.tex-text').show();
                                });
                            }
                        });
                    }
                });
            } else {
                MathJax.Hub.Queue(['Typeset', MathJax.Hub, $content[0]], function () {
                    $content.find('.tex-image').hide();
                    $content.find('.tex-text').show();
                });
            }
        }
    })
});