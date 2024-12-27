from django_ace.widgets import AceWidget as OldAceWidget

__all__ = ['AceWidget', 'AdminAceWidget']


class AceWidget(OldAceWidget):
    pass


class AdminAceWidget(OldAceWidget):
    class Media:
        css = {
            'all': ['ace-dmoj.css'],
        }
