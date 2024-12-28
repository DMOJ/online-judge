from martor.widgets import AdminMartorWidget as OldAdminMartorWidget, MartorWidget as OldMartorWidget

__all__ = ['MartorWidget', 'AdminMartorWidget']


class MartorWidget(OldMartorWidget):
    class Media:
        js = ['martor-mathjax.js']


class AdminMartorWidget(OldAdminMartorWidget):
    UPLOADS_ENABLED = True

    class Media:
        css = {
            'all': ['martor-description.css', 'featherlight.css'],
        }
        js = ['admin/js/jquery.init.js', 'martor-mathjax.js', 'libs/featherlight/featherlight.min.js']
