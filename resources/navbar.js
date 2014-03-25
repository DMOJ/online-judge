$(function () {
    var nav_offset = $('#navigation').offset().top;
    $(window).scroll(function () {
        $('#navigation').css('position', ($(window).scrollTop() - nav_offset > 0) ? 'fixed' : 'relative');
    });
    var float_bar = $('.info-float');
    var info_offset = float_bar.offset().top;
    var info_right = float_bar.offset().right;
    $(window).scroll(function () {
        float_bar.css('position', ($(window).scrollTop() - info_offset > 0) ? 'fixed' : 'relative');
        float_bar.css('right', ($(window).scrollTop() - info_offset > 0) ? info_right : 'auto');
    });
});
