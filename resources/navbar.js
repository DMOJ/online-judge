$(function () {
    var nav_offset = $('#navigation').offset().top;
    $(window).scroll(function () {
        $('#navigation').css('position', ($(window).scrollTop() - nav_offset > 0) ? 'fixed' : 'relative');
    });
    var float = $('.info-float');
    var info_offset = float.offset().top;
    var info_right = float.offset().right;
    $(window).scroll(function () {
        float.css('position', ($(window).scrollTop() - info_offset > 0) ? 'fixed' : 'relative');
        float.css('right', ($(window).scrollTop() - info_offset > 0) ? 0 : 'auto');
    });
});
