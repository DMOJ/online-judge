var active_tooltip = null;

function display_tooltip(where) {
    if (active_tooltip !== null) {
        active_tooltip.removeClass(['tooltipped', 'tooltipped-e', 'tooltipped-w']).removeAttr('aria-label');
    }
    if (where !== null) {
        var day_num = parseInt(where.attr('data-day'));
        var tooltip_direction = day_num < 183 ? 'tooltipped-e' : 'tooltipped-w';
        where.addClass(['tooltipped', tooltip_direction])
            .attr('aria-label', where.attr('data-submission-activity'));
    }
    active_tooltip = where;
}

function install_tooltips($) {
    display_tooltip(null);
    $('.activity-label').each(function () {
        var link = $(this);
        link.hover(
            function (e) {
                display_tooltip(link);
            },
            function (e) {
                display_tooltip(null);
            }
        );
    });
}

function init_submission_table($, submission_activity, metadata, language_code) {
    var activity_levels = 5; // 5 levels of activity
    var current_year = new Date().getFullYear();
    var $div = $('#submission-activity');

    function draw_contribution(year) {
        $div.find('#submission-activity-table td').remove();
        $div.find('#year').attr('data-year', year);
        $div.find('#prev-year-action').css('display', year > (metadata.min_year || current_year) ? '' : 'none');
        $div.find('#next-year-action').css('display', year < current_year ? '' : 'none');

        var start_day = new Date(year, 0, 1);
        var end_day = new Date(year + 1, 0, 0);
        if (year == current_year) {
            end_day = new Date();
            start_day = new Date(end_day.getFullYear() - 1, end_day.getMonth(), end_day.getDate() + 1);
            $div.find('#year').text(gettext('past year'));
        } else {
            $div.find('#year').text(year);
        }
        var days = [];
        for (var day = start_day, day_num = 1; day <= end_day; day.setDate(day.getDate() + 1), day_num++) {
            var isodate = day.toISOString().split('T')[0];
            days.push({
                date: new Date(day),
                weekday: day.getDay(),
                day_num: day_num,
                activity: submission_activity[isodate] || 0,
            });
        }

        var sum_activity = days.reduce(function (sum, obj) { return sum + obj.activity; }, 0);
        $div.find('#submission-total-count').text(
            ngettext('%(cnt)d total submission', '%(cnt)d total submissions', sum_activity)
                .replace('%(cnt)d', sum_activity)
        );
        if (year == current_year) {
            $('#submission-activity-header').text(
                ngettext('%(cnt)d submission in the last year', '%(cnt)d submissions in the last year', sum_activity)
                    .replace('%(cnt)d', sum_activity)
            );
        } else {
            $('#submission-activity-header').text(
                ngettext('%(cnt)d submission in %(year)d', '%(cnt)d submissions in %(year)d', sum_activity)
                    .replace('%(cnt)d', sum_activity)
                    .replace('%(year)d', year)
            );
        }

        for (var current_weekday = 0; current_weekday < days[0].weekday; current_weekday++) {
            $div.find('#submission-' + current_weekday)
                .append($('<td>').addClass('activity-blank').append('<div>'));
        }

        var max_activity = Math.max(1, Math.max.apply(null, days.map(function (obj) { return obj.activity; })));
        days.forEach(function (obj) {
            var level = Math.ceil((obj.activity / max_activity) * (activity_levels - 1));
            var text = ngettext('%(cnt)d submission on %(date)s', '%(cnt)d submissions on %(date)s', obj.activity)
                .replace('%(cnt)d', obj.activity)
                .replace(
                    '%(date)s',
                    obj.date.toLocaleDateString(
                        language_code,
                        { month: 'short', year: 'numeric', day: 'numeric' }
                    )
                );

            $div.find('#submission-' + obj.weekday)
                .append(
                    $('<td>').addClass(['activity-label', 'activity-' + level])
                        .attr('data-submission-activity', text)
                        .attr('data-day', obj.day_num)
                        .append('<div>')
                );
        });

        install_tooltips($);
    }

    $('#prev-year-action').click(function () {
        draw_contribution(parseInt($div.find('#year').attr('data-year')) - 1);
    });
    $('#next-year-action').click(function () {
        draw_contribution(parseInt($div.find('#year').attr('data-year')) + 1);
    });

    draw_contribution(current_year);
    $('#submission-activity').css('display', '');
}

window.init_submission_table = init_submission_table;
