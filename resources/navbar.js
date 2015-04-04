function featureTest(property, value, noPrefixes) {
    var prop = property + ':',
        el = document.createElement('test'),
        mStyle = el.style;

    if (!noPrefixes) {
        mStyle.cssText = prop + ['-webkit-', '-moz-', '-ms-', '-o-', ''].join(value + ';' + prop) + value + ';';
    } else {
        mStyle.cssText = prop + value;
    }
    return !!mStyle[property];
}

window.fix_div = function (div, height, right, fake_gen) {
    var div_offset = div.offset().top;
    if (right)
        var div_right = $(window).width() - div.offset().left - div.outerWidth();
    var is_moving;
    if (typeof fake_gen !== 'undefined')
        var fake = fake_gen(div);
    var moving = function () {
        div.css('position', 'absolute').css('top', div_offset);
        is_moving = true;
    };
    var fix = function () {
        div.css('position', 'fixed').css('top', height);
        is_moving = false;
    };
    if (right)
        div.css('right', div_right);
    if (typeof fake != 'undefined') {
        div.css('left', fake.offset().left).css('right', undefined);
        $(window).resize(function () {
            div.css('left', fake.offset().left);
        });
    }
    ($(window).scrollTop() - div_offset > -height) ? fix() : moving();
    $(window).scroll(function () {
        if (($(window).scrollTop() - div_offset > -height) == is_moving)
            is_moving ? fix() : moving();
    });
};

$(function () {
    fix_div($('#navigation'), 0, false, function (nav) {
        $('<div/>', {id: 'fake-nav'}).css('height', nav.height()).prependTo('#nav-head');
    });

    var $nav_list = $('#nav-list');
    $('#navicon').click(function (event) {
        event.stopPropagation();
        $nav_list.show();
        $nav_list.click(function (event) {
            event.stopPropagation();
        });
        $('html').click(function () {
            $nav_list.hide();
        });
    });
});
