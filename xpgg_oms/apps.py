from django.apps import AppConfig


class XpggOmsConfig(AppConfig):
    name = 'xpgg_oms'

    def ready(self):
        import xpgg_oms.signals
