window.timezone_picker = function ($map, $field, json_data) {
    var $axisX = $map.find('.map-axis-x'),
        $axisY = $map.find('.map-axis-y'),
        width = $map.outerWidth(),
        height = $map.outerHeight(),
        lastCenter,
        centers = [];

    $(window).resize(function () {
        width = $map.outerWidth();
        height = $map.outerHeight();
    }).resize();

    function changeCenter(center) {
        if (center === lastCenter) {
            return;
        }
        if (lastCenter) {
            lastCenter.deactivate();
        }
        center.activate();
        lastCenter = center;
    }

    function Center(data) {
        this.name = data.name;
        this.x = (180 + data['long']) / 360;
        this.y = (90 - data.lat) / 180;
        this.dom = $('<span>').appendTo($map).css({
            left: this.x * 100 + '%',
            top: this.y * 100 + '%'
        });
        if (this.name === $field.val())
            changeCenter(this);
    }

    Center.prototype = {
        distSqr: function (x, y) {
            var dx = this.x - x,
                dy = this.y - y;
            return dx * dx + dy * dy;
        },
        activate: function () {
            if ($field.val() != this.name)
                $field.val(this.name).trigger('change');
            $axisX.css('left', this.x * 100 + '%');
            $axisY.css('top', this.y * 100 + '%');
        },
        deactivate: function () {
            this.dom.removeClass('active');
        }
    };

    $.getJSON(json_data).then(function (data) {
        for (var name in data.zones)
            centers.push(new Center(data.zones[name]));
    });

    $map.click(function (e) {
        var offset = $(this).offset(),
            x = e.pageX - offset.left,
            y = e.pageY - offset.top,
            px = x / width,
            py = y / height,
            dist,
            closestDist = 100,
            closestCenter,
            i;

        for (i = 0; i < centers.length; i++) {
            dist = centers[i].distSqr(px, py);
            if (dist < closestDist) {
                closestCenter = centers[i];
                closestDist = dist;
            }
        }

        if (closestCenter) {
            changeCenter(closestCenter);
        }
    });

    $field.change(function(e) {
        var tz = $(this).val();
        for (var i = 0; i < centers.length; i++)
            if (centers[i].name == tz) {
                changeCenter(centers[i]);
                break;
            }
    })
};
