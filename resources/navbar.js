$(function() {
    (function() {
        var nav_offset = $('#navigation').offset().top;
        $(window).scroll(function() {
            $('#navigation').css('position', ($(window).scrollTop() - nav_offset > 0) ? 'fixed' : 'relative');
        });
    })();
});
