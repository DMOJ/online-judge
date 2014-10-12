function count_down(label) {
    var match = /(\d+):(\d+):(\d+)/.exec(label.text());
    var time = parseInt(match[1]) * 3600 + parseInt(match[2]) * 60 + parseInt(match[3]);

    function format(num) {
        var s = "0" + num;
        return s.substr(s.length - 2);
    }

    var timer = setInterval(function () {
        --time;
        if (time <= 0)
            clearInterval(timer);
        var h = Math.floor(time / 3600);
        var m = Math.floor(time % 3600 / 60);
        var s = time % 60;
        label.text(format(h) + ":" + format(m) + ":" + format(s));
    }, 1000);
}
