from pyramid.testing import DummyResource

from zope.interface import Interface
from zope.interface import implementer


class IRoot(Interface):
    pass

class IOrganisation(Interface):
    pass


@implementer(IRoot)
class Root(DummyResource):
    pass

@implementer(IOrganisation)
class Organisation(DummyResource):
    pass
