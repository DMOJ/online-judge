$(function () {
    window.register_dmmd_preview = function ($preview) {
        var $update = $preview.find('.dmmd-preview-update');
        var $content = $preview.find('.dmmd-preview-content');
        var preview_url = $preview.attr('data-preview-url');

        $update.click(function () {
            var $textarea = $('#' + $preview.attr('data-textarea-id'));
            $.post(preview_url, {
                preview: $textarea.val(),
                csrfmiddlewaretoken: $.cookie('csrftoken')
            }, function (result) {
                $content.html(result);
            });
        }).click();
    };

    $('.dmmd-preview').each(function () {
        register_dmmd_preview($(this));
    });
});
