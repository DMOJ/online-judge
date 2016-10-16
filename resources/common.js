// IE 8
if (!Array.indexOf) {
    Array.prototype.indexOf = function (obj) {
        for (var i = 0; i < this.length; i++) {
            if (this[i] == obj) {
                return i;
            }
        }
        return -1;
    }
}

// http://stackoverflow.com/a/1060034/1090657
$(function () {
    var hidden = 'hidden';

    // Standards:
    if (hidden in document)
        document.addEventListener('visibilitychange', onchange);
    else if ((hidden = 'mozHidden') in document)
        document.addEventListener('mozvisibilitychange', onchange);
    else if ((hidden = 'webkitHidden') in document)
        document.addEventListener('webkitvisibilitychange', onchange);
    else if ((hidden = 'msHidden') in document)
        document.addEventListener('msvisibilitychange', onchange);
    // IE 9 and lower:
    else if ('onfocusin' in document)
        document.onfocusin = document.onfocusout = onchange;
    // All others:
    else
        window.onpageshow = window.onpagehide
            = window.onfocus = window.onblur = onchange;

    function onchange(evt) {
        var v = 'window-visible', h = 'window-hidden', evtMap = {
            focus: v, focusin: v, pageshow: v, blur: h, focusout: h, pagehide: h
        };

        evt = evt || window.event;
        if (evt.type in evtMap)
            document.body.className = evtMap[evt.type];
        else
            document.body.className = this[hidden] ? 'window-hidden' : 'window-visible';

        if ('$' in window)
            $(window).trigger('dmoj:' + document.body.className);
    }

    // set the initial state (but only if browser supports the Page Visibility API)
    if (document[hidden] !== undefined)
        onchange({type: document[hidden] ? 'blur' : 'focus'});
});

function register_toggle(link) {
    link.click(function () {
        var toggled = link.next('.toggled');
        if (toggled.is(':visible')) {
            toggled.hide(400);
            link.removeClass('open');
            link.addClass('closed');
        } else {
            toggled.show(400);
            link.addClass('open');
            link.removeClass('closed');
        }
    });
}

$(function register_all_toggles() {
    $('.toggle').each(function () {
        register_toggle($(this));
    });
});

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

window.fix_div = function (div, height) {
    var div_offset = div.offset().top - $('html').offset().top;
    var is_moving;
    var moving = function () {
        div.css('position', 'absolute').css('top', div_offset);
        is_moving = true;
    };
    var fix = function () {
        div.css('position', 'fixed').css('top', height);
        is_moving = false;
    };
    ($(window).scrollTop() - div_offset > -height) ? fix() : moving();
    $(window).scroll(function () {
        if (($(window).scrollTop() - div_offset > -height) == is_moving)
            is_moving ? fix() : moving();
    });
};

$(function () {
    if (typeof window.orientation !== 'undefined') {
        $(window).resize(function () {
            var width = Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
            $('#viewport').attr('content', width > 480 ? 'initial-scale=1' : 'width=480');
        });
    }

    var $nav_list = $('#nav-list');
    $('#navicon').click(function (event) {
        event.stopPropagation();
        $nav_list.toggle();
        if ($nav_list.is(':hidden'))
            $(this).blur().removeClass('hover');
        else {
            $(this).addClass('hover');
            $nav_list.find('li ul').css('left', $('#nav-list').width()).hide();
        }
    }).hover(function () {
        $(this).addClass('hover');
    }, function () {
        $(this).removeClass('hover');
    });
    
    $nav_list.find('li a .nav-expand').click(function (event) {
        event.preventDefault();
        $(this).parent().siblings('ul').css('display', 'block');
    });

    $nav_list.find('li a').each(function () {
        if (!$(this).siblings('ul').length)
            return;
        $(this).on('contextmenu', function (event) {
            event.preventDefault();
        }).on('taphold', function () {
            $(this).siblings('ul').css('display', 'block');
        });
    });

    $nav_list.click(function (event) {
        event.stopPropagation();
    });

    $('html').click(function () {
        $nav_list.hide();
    });

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^(GET|HEAD|OPTIONS|TRACE)$/.test(settings.type)) && !this.crossDomain)
                xhr.setRequestHeader('X-CSRFToken', $.cookie('csrftoken'));
        }
    });
});

if (!Date.now) {
    Date.now = function () {
        return new Date().getTime();
    };
}

function count_down(label) {
    var initial = parseInt(label.attr('data-secs'));
    var start = Date.now();

    function format(num) {
        var s = "0" + num;
        return s.substr(s.length - 2);
    }

    var timer = setInterval(function () {
        var time = Math.round(initial - (Date.now() - start) / 1000);
        if (time <= 0)
            clearInterval(timer);
        var d = Math.floor(time / 86400);
        var h = Math.floor(time % 86400 / 3600);
        var m = Math.floor(time % 3600 / 60);
        var s = time % 60;
        if (d > 0)
            label.text(npgettext('time format with day', '%d day %h:%m:%s', '%d days %h:%m:%s', d)
                .replace('%d', d).replace('%h', format(h)).replace('%m', format(m)).replace('%s', format(s)));
        else
            label.text(pgettext('time format without day', '%h:%m:%s')
                .replace('%h', format(h)).replace('%m', format(m)).replace('%s', format(s)));
    }, 1000);
}

window.register_update_relative = function (get_times, show_relative, interval) {
    if (typeof interval === 'undefined')
        interval = 60000;

    if (typeof show_relative === 'undefined')
        show_relative = function (time) {
            return Math.abs(moment().diff(time, 'days')) < 1;
        };

    function update_relative_time($time) {
        var when = moment($time.attr('data-unix'));
        if (show_relative(when))
            $time.find('.relative').text(when.fromNow());
        else
            $time.addClass('too-long-ago');
    }

    setInterval(function update() {
        get_times().filter(':not(.too-long-ago)').each(function () {
            update_relative_time($(this));
        });
        return update;
    }(), interval);

    return update_relative_time;
};

// Placeholder polyfill
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
