"""Data backend for Django
"""

from datetime import datetime, timedelta

from django.db.models import F, Sum

from .. import models

class Backend(object):
    def __init__(self, device=None):
        if isinstance(device, str):
            self.device_id = device
        else:
            self.device_id = device.device_id
    def count(self, slc=None):
        if slc is not None:
            qs = self[slc]
            if qs is None: return 0
            return qs.count()
        return models.Data.objects.filter(device_id=self.device_id).count()
    def bytes_total(self):
        return models.Data.objects.filter(device_id=self.device_id).aggregate(sum=Sum(F('data_length')))['sum']
    def __getitem__(self, slc):
        qs = models.Data.objects.filter(device_id=self.device_id).order_by('ts')
        #import IPython ; IPython.embed()
        if not qs.exists():
            return None
        if isinstance(slc, int):
            if slc < 0:
                idx = -slc - 1   # -1=>0, -2=>1, etc
                return qs.reverse()[idx]
            return qs[slc]
        if isinstance(slc, slice):
            if isinstance(slc.start, datetime):
                qs = qs.filter(ts__gte=slc.start)
            if isinstance(slc.stop, datetime):
                qs = qs.filter(ts__lt=slc.stop)
        return qs
