import logging

from urllib3 import Retry

logger = logging.getLogger(__name__)


class CallbackRetry(Retry):

    def __init__(self, *args, **kwargs):
        self._callback = kwargs.pop('callback', None)
        super(CallbackRetry, self).__init__(*args, **kwargs)

    def new(self, **kw):
        # pass along the subclass additional information when creating
        # a new instance.
        kw['callback'] = self._callback
        return super(CallbackRetry, self).new(**kw)

    def increment(self, method, url, *args, **kwargs):
        if self._callback:
            try:
                self._callback()
            except Exception:
                logger.exception('Callback raised an exception, ignoring')
        return super(CallbackRetry, self).increment(method, url, *args, **kwargs)