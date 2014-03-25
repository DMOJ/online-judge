$(function () {
    var nav_offset = $('#navigation').offset().top;
    $(window).scroll(function () {
        $('#navigation').css('position', ($(window).scrollTop() - nav_offset > 0) ? 'fixed' : 'relative');
    });
    var info_offset = $('.info-float').offset().top;
    $(window).scroll(function () {
        $('.info-float').css('position', ($(window).scrollTop() - info_offset > 0) ? 'fixed' : 'relative');
    });
});
