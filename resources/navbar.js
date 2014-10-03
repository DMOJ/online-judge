$(function () {
    var nav = $('#navigation');
    var nav_offset = nav.offset().top;
    $('<div/>', {id: 'fake-nav'}).css('height', nav.height()).prependTo('#nav-head');
    var moving = function () {
        nav.css('position', 'absolute').css('top', nav_offset);
    };
    var fix = function () {
        nav.css('position', 'fixed').css('top', 0);
    };
    moving();
    $(window).scroll(function () {
        ($(window).scrollTop() - nav_offset > 0) ? fix() : moving();
    });
});
