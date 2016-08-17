$(function () {
    window.register_dmmd_preview = function ($preview) {
        var $update = $preview.find('.dmmd-preview-update');
        var $content = $preview.find('.dmmd-preview-content');
        var preview_url = $preview.attr('data-preview-url');

        $update.click(function () {
            var text = $('#' + $preview.attr('data-textarea-id')).val();
            if (text) {
                $.post(preview_url, {
                    preview: text,
                    csrfmiddlewaretoken: $.cookie('csrftoken')
                }, function (result) {
                    $content.html(result);
                    $preview.addClass('dmmd-preview-content');
                });
            } else {
                $content.empty();
                $preview.removeClass('dmmd-preview-content');
            }
        }).click();
    };

    $('.dmmd-preview').each(function () {
        register_dmmd_preview($(this));
    });

    if ('django' in window && 'jQuery' in window.django)
        django.jQuery(document).on('formset:added', function(event, $row) {
            var $preview = $row.find('.dmmd-preview');
            if ($preview.length) {
                var id = $row.attr('id');
                id = id.substr(id.lastIndexOf('-') + 1);
                $preview.attr('data-textarea-id', $preview.attr('data-textarea-id').replace('__prefix__', id));
                register_dmmd_preview($preview);
            }
        });
});
