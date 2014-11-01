String.prototype.format = function () {
    var formatted = this;
    for (var i = 0; i < arguments.length; i++) {
        var regexp = new RegExp('\\{' + i + '\\}', 'gi');
        formatted = formatted.replace(regexp, arguments[i]);
    }
    return formatted;
};

String.prototype.replaceAll = function (find, replace) {
    var str = this;
    return str.replace(new RegExp(find.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'), 'g'), replace);
};

Array.prototype.removeAll = function (what) {
    var array = this;
    for (var i = array.length - 1; i--;) {
        if (array[i] === what) array.splice(i, 1);
    }
};

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

$(function () {
    $('.toggle').click(function () {
        var a = $(this);
        var types = $('#' + a.attr('id') + '-toggle');
        if (types.is(':visible')) {
            types.hide(400);
            a.removeClass('open');
            a.addClass('closed');
        } else {
            types.show(400);
            a.addClass('open');
            a.removeClass('closed');
        }
    });
});