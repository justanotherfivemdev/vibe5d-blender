__all__ = [
    ,
,
,
,
,
,
]

try:
    import ssl
    from ssl import SSLError, SSLEOFError, SSLWantReadError, SSLWantWriteError

    HAVE_SSL = True
except ImportError:

    class SSLError(Exception):
        pass


    class SSLEOFError(Exception):
        pass


    class SSLWantReadError(Exception):
        pass


    class SSLWantWriteError(Exception):
        pass


    ssl = None
    HAVE_SSL = False
