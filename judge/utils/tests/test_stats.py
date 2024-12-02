from django.test import SimpleTestCase

from judge.utils.stats import chart_colors, get_bar_chart, get_pie_chart, highlight_colors


class StatsTestCase(SimpleTestCase):
    def test_get_bar_chart(self):
        self.assertEquals(
            get_pie_chart([]),
            {
                'labels': [],
                'datasets': [
                    {
                        'backgroundColor': chart_colors,
                        'highlightBackgroundColor': highlight_colors,
                        'data': [],
                    },
                ],
            },
        )
        self.assertEquals(
            get_pie_chart([('label', 10, 'random')]),
            {
                'labels': ['label'],
                'datasets': [
                    {
                        'backgroundColor': chart_colors,
                        'highlightBackgroundColor': highlight_colors,
                        'data': [10],
                    },
                ],
            },
        )
        self.assertEquals(
            get_pie_chart([('label1', 0), ('label2', 10)]),
            {
                'labels': ['label1', 'label2'],
                'datasets': [
                    {
                        'backgroundColor': chart_colors,
                        'highlightBackgroundColor': highlight_colors,
                        'data': [0, 10],
                    },
                ],
            },
        )

    def test_get_pie_chart(self):
        self.assertEquals(
            get_bar_chart([]),
            {
                'labels': [],
                'datasets': [
                    {
                        'backgroundColor': 'rgba(151,187,205,0.5)',
                        'borderColor': 'rgba(151,187,205,0.8)',
                        'borderWidth': 1,
                        'hoverBackgroundColor': 'rgba(151,187,205,0.75)',
                        'hoverBorderColor': 'rgba(151,187,205,1)',
                        'data': [],
                    },
                ],
            },
        )
        self.assertEquals(
            get_bar_chart([('label1', 10, 'random')]),
            {
                'labels': ['label1'],
                'datasets': [
                    {
                        'backgroundColor': 'rgba(151,187,205,0.5)',
                        'borderColor': 'rgba(151,187,205,0.8)',
                        'borderWidth': 1,
                        'hoverBackgroundColor': 'rgba(151,187,205,0.75)',
                        'hoverBorderColor': 'rgba(151,187,205,1)',
                        'data': [10],
                    },
                ],
            },
        )
        self.assertEquals(
            get_bar_chart(
                [('label1', 0), ('label2', 10)],
                fillColor='#aaa',
                strokeColor='#bbb',
                highlightFill='#ccc',
                highlightStroke='#ddd',
            ),
            {
                'labels': ['label1', 'label2'],
                'datasets': [
                    {
                        'backgroundColor': '#aaa',
                        'borderColor': '#bbb',
                        'borderWidth': 1,
                        'hoverBackgroundColor': '#ccc',
                        'hoverBorderColor': '#ddd',
                        'data': [0, 10],
                    },
                ],
            },
        )
