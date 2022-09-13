var voteChart = null;

function init_problem_vote_form() {
    $('#delete-problem-vote-form').on('submit', function (e) {
        e.preventDefault();
        $.ajax({
            url: $('#delete-problem-vote-form').prop('action'),
            type: 'POST',
            data: $('#delete-problem-vote-form').serialize(),
            success: function () {
                $('#problem-vote-button').text(gettext('Vote on problem points'));
                $.featherlight.close();
            },
            error: function (data) {
                var msg = 'responseJSON' in data ? data.responseJSON.message : data.statusText;
                alert(interpolate(gettext('Unable to delete vote: %s'), [msg]));
            }
        });
    });

    $('#problem-vote-form').on('submit', function (e) {
        e.preventDefault();
        $.ajax({
            url: $('#problem-vote-form').prop('action'),
            type: 'POST',
            data: $('#problem-vote-form').serialize(),
            success: function (data) {
                $('#problem-vote-button').text(interpolate(gettext('Edit points vote (%s)'), [data.points]));
                $.featherlight.close();
            },
            error: function (data) {
                var errors = 'responseJSON' in data ? data.responseJSON : {'message': data.statusText};
                if ('message' in errors) {
                    alert(interpolate(gettext('Unable to cast vote: %s'), [errors.message]));
                }
                $('#points-error').text('points' in errors ? errors.points[0] : '');
                $('#note-error').text('note' in errors ? errors.note[0] : '');
            }
        });
    });
}

function reload_problem_vote_graph(data, min_possible_vote, max_possible_vote) {
    if (voteChart !== null) voteChart.destroy();

    // Give the graph some padding on both sides.
    var min_points = Math.max(data[0] - 2, min_possible_vote);
    var max_points = Math.min(data[data.length - 1] + 2, max_possible_vote);

    var xlabels = [];
    var voteFreq = [];
    for (var i = min_points; i <= max_points; i++) {
        xlabels.push(i);
        voteFreq.push(0);
    }

    data.forEach(function (x) { voteFreq[x - min_points]++; });
    var max_number_of_votes = Math.max.apply(null, voteFreq);

    var voteData = {
        labels: xlabels,
        datasets: [{
            label: gettext('Number of votes for this point value'),
            data: voteFreq,
            borderColor: 'red',
            backgroundColor: 'pink',
        }],
    };
    var voteDataConfig = {
        type: 'bar',
        data: voteData,
        options: {
            responsive: true,
            scales: {
                yAxes: [{
                    ticks: {
                        precision: 0,
                        suggestedMax: Math.ceil(max_number_of_votes * 1.2),
                        beginAtZero: true,
                    }
                }],
                xAxes: [{
                    ticks: {
                        beginAtZero: false,
                    }
                }],
            },
        },
    };
    voteChart = new Chart($('#problem-vote-chart').get(0), voteDataConfig);
}
