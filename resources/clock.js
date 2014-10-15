function count_down(label) {
    var match = /(?:(\d+)\s+days?\s+)?(\d+):(\d+):(\d+)/.exec(label.text());
    var time = parseInt(match[2]) * 3600 + parseInt(match[3]) * 60 + parseInt(match[4]);
    if (typeof match[1] != 'undefined')
        time += parseInt(match[1]) * 86400;

    function format(num) {
        var s = "0" + num;
        return s.substr(s.length - 2);
    }

    var timer = setInterval(function () {
        --time;
        if (time <= 0)
            clearInterval(timer);
        var d = Math.floor(time / 86400);
        var h = Math.floor(time % 86400 / 3600);
        var m = Math.floor(time % 3600 / 60);
        var s = time % 60;
        var days = d > 0 ? d + ' day' + 's '.substr(d == 1) : '';
        label.text(days + format(h) + ":" + format(m) + ":" + format(s));
    }, 1000);
}
