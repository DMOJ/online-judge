$('input[placeholder]').each(function() {
    if ($(this).val() == '') {

        $(this).val($(this).attr('placeholder'));
        $(this).focus(function() {
            if ($(this).val() == $(this).attr('placeholder')) $(this).val('');

        });
        $(this).blur(function() {
            if ($(this).val() == '') {
                $(this).val($(this).attr('placeholder'));
            }
        });
    }
});

$('form').submit(function(evt) {
    $('input[placeholder]').each(function() {
        if ($(this).attr('placeholder') == $(this).val()) {
            $(this).val('');
        }
    });
    evt.preventDefault();
});
