from martor.widgets import AdminMartorWidget as OldAdminMartorWidget, MartorWidget as OldMartorWidget

__all__ = ['MartorWidget', 'AdminMartorWidget']


class DMOJMartorMixin:
    class Media:
        css = {
            'all': ['martor-description.css'],
        }


class MartorWidget(DMOJMartorMixin, OldMartorWidget):
    pass


class AdminMartorWidget(DMOJMartorMixin, OldAdminMartorWidget):
    pass
