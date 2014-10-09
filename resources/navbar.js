window.fix_div = function (div, height, right, fake_gen) {
    var div_offset = div.offset().top;
    var is_moving = false;
    if (typeof fake_gen !== 'undefined') {
        var fake_info = fake_gen(div);
        var fake = $('<div/>', {id: fake_info.id});
        delete fake_info.id;
        fake.css(fake_info);
    }
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
    if (typeof fake_gen !== 'undefined') {
        return fake;
    }
};

$(function () {
    fix_div($('#navigation'), 0, false, function (nav) {
        return {
            height: nav.height(),
            id: 'fake-nav'
        };
    }).prependTo('#nav-head');
});
