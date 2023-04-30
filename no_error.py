import functools


def no_error(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except Exception as e:
            print(f'NE: {e.__class__.__name__}: {e.args}')
    return wrapper