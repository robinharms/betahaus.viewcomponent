from zope.interface import implementer
from pyramid.security import has_permission
from pyramid.traversal import find_interface

from betahaus.viewcomponent.interfaces import IViewGroup


@implementer(IViewGroup)
class ViewGroup(object):
    """ Named utility for views. Behaves like an ordered dict with some extra funkyness.
        See interfaces.py for documentation.
    """
    
    def __init__(self, name = None, perm_checker = None):
        self.name = name
        if perm_checker is None:
            perm_checker = has_permission
        self.perm_checker = perm_checker
        self._order = []
        self._data = {}
    
    def __call__(self, context, request, **kw):
        try:
            return "".join([va(context, request, **kw) for va in self.get_context_vas(context, request)])
        except Exception:
            #This structure might look silly, but the point of it is to provide useful
            #traceback while not slowing down a normal call.
            for va in self.get_context_vas(context, request):
                try:
                    output = va(context, request, **kw)
                except Exception as exc:
                    eargs = list(exc.args)
                    eargs[0] = "ViewAction '%s' of ViewGroup '%s' raised an exception: %s" % (va.name, self.name, exc.args[0])
                    exc.args = eargs
                    raise exc
                if not isinstance(output, basestring):
                    raise TypeError("ViewAction '%s' of ViewGroup '%s' didn't return a string. Output was: %s" % (va.name, self.name, output))

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        assert isinstance(value, ViewAction)
        self._data[key] = value
        if key not in self._order:
            self._order.append(key)

    def __delitem__(self, key):
        del self._data[key]
        if key in self._order:
            self._order.remove(key)

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data

    def _get_order(self):
        return self._order
    def _set_order(self, value):
        handle_keys = set(self.order)
        value = [unicode(x) for x in value]
        for val in value:
            if val not in self:
                raise KeyError("You can't set order with key '%s' since it doesn't exist in this util." % val)
            handle_keys.remove(val)
        for unhandled_key in handle_keys:
            value.append(unhandled_key)
        self._order = value
    order = property(_get_order, _set_order)

    def get_context_vas(self, context, request):
        for va in self.values():
            if va.interface and not va.interface.providedBy(context):
                continue
            if va.permission and not self.perm_checker(va.permission, context, request):
                continue
            if va.containment and not find_interface(context, va.containment):
                continue
            yield va

    def add(self, view_action):
        self[view_action.name] = view_action

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self.order

    def values(self):
        return [self[key] for key in self.order]

    def items(self):
        return [(name, self[name]) for name in self.order]

    def __repr__(self): # pragma : no cover
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return "<%s '%s'>" % (classname, self.name)


class ViewAction(object):

    def __init__(self, _callable, name, title = u"",
                 permission = None, interface = None, containment = None, **kw):
        assert callable(_callable)
        assert isinstance(name, basestring)
        self.callable = _callable
        self.name = name
        self.title = title
        self.permission = permission
        self.interface = interface
        self.containment = containment
        self.kwargs = kw

    def __call__(self, context, request, **kw):
        return self.callable(context, request, self, **kw)

    def __repr__(self): # pragma : no cover
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return "<%s '%s'>" % (classname, self.name)
