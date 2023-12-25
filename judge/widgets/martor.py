from martor.widgets import AdminMartorWidget as OldAdminMartorWidget, MartorWidget as OldMartorWidget

__all__ = ['MartorWidget', 'AdminMartorWidget']


class MartorWidget(OldMartorWidget):
    class Media:
        css = {
            'all': ['martor-description.css'],
        }
        js = ['martor-mathjax.js']


class AdminMartorWidget(OldAdminMartorWidget):
    class Media:
        css = MartorWidget.Media.css
        js = ['admin/js/jquery.init.js', 'martor-mathjax.js']
