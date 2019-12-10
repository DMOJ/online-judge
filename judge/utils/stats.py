from operator import itemgetter

__all__ = ('chart_colors', 'highlight_colors', 'get_pie_chart', 'get_bar_chart')


chart_colors = [0x3366CC, 0xDC3912, 0xFF9900, 0x109618, 0x990099, 0x3B3EAC, 0x0099C6, 0xDD4477, 0x66AA00, 0xB82E2E,
                0x316395, 0x994499, 0x22AA99, 0xAAAA11, 0x6633CC, 0xE67300, 0x8B0707, 0x329262, 0x5574A6, 0x3B3EAC]


highlight_colors = []


def _highlight_colors():
    for color in chart_colors:
        r, g, b = color >> 16, (color >> 8) & 0xFF, color & 0xFF
        highlight_colors.append('#%02X%02X%02X' % (min(int(r * 1.2), 255),
                                                   min(int(g * 1.2), 255),
                                                   min(int(b * 1.2), 255)))


_highlight_colors()


chart_colors = list(map('#%06X'.__mod__, chart_colors))


def get_pie_chart(data):
    return {
        'labels': list(map(itemgetter(0), data)),
        'datasets': [
            {
                'backgroundColor': chart_colors,
                'highlightBackgroundColor': highlight_colors,
                'data': list(map(itemgetter(1), data)),
            },
        ],
    }


def get_bar_chart(data, **kwargs):
    return {
        'labels': list(map(itemgetter(0), data)),
        'datasets': [
            {
                'backgroundColor': kwargs.get('fillColor', 'rgba(151,187,205,0.5)'),
                'borderColor': kwargs.get('strokeColor', 'rgba(151,187,205,0.8)'),
                'borderWidth': 1,
                'hoverBackgroundColor': kwargs.get('highlightFill', 'rgba(151,187,205,0.75)'),
                'hoverBorderColor': kwargs.get('highlightStroke', 'rgba(151,187,205,1)'),
                'data': list(map(itemgetter(1), data)),
            },
        ],
    }
