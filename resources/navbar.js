$(function () {
    var nav = $('#navigation');
    var nav_offset = nav.offset().top;
    $('<div/>', {id: 'fake-nav'}).css('height', nav.height()).prependTo('#nav-head');
    var is_moving = false;
    var moving = function () {
        if (!is_moving) {
            nav.css('position', 'absolute').css('top', nav_offset);
            is_moving = true;
        }
    };
    var fix = function () {
        if (is_moving) {
            nav.css('position', 'fixed').css('top', 0);
            is_moving = false;
        }
    };
    moving();
    $(window).scroll(function () {
        ($(window).scrollTop() - nav_offset > 0) ? fix() : moving();
    });
});

function fix_div(div, height, right) {
    var div_offset = div.offset().top;
    var is_moving = false;
    var moving = function () {
        if (!is_moving) {
            div.css('position', 'absolute').css('top', div_offset);
            is_moving = true;
        }
    };
    var fix = function () {
        if (is_moving) {
            div.css('position', 'fixed').css('top', height);
            is_moving = false;
        }
    };
    if (right) div.css('right', $(window).width() - div.offset().left - div.outerWidth());
    moving();
    $(window).scroll(function () {
        ($(window).scrollTop() - div_offset > -height) ? fix() : moving();
    });
}