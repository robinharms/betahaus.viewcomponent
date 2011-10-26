from unittest import TestCase

from pyramid import testing
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from betahaus.viewcomponent.interfaces import IViewGroup
from betahaus.viewcomponent.fixtures import contexts


def _dummy_callable(*args):
    return "".join([str(x) for x in args])

def _callable_text(context, request, va):
    return "%s, %s, %s" % (context.__class__, request.__class__, str(va))


class ViewGroupTests(TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from betahaus.viewcomponent import ViewGroup
        return ViewGroup

    @property
    def _view_action(self):
        from betahaus.viewcomponent import ViewAction
        return ViewAction

    def test_verify_class(self):
        self.failUnless(verifyClass(IViewGroup, self._cut))

    def test_verify_obj(self):
        self.failUnless(verifyObject(IViewGroup, self._cut()))

    def test_add(self):
        obj = self._cut()
        va = self._view_action(_dummy_callable, 'name')
        obj.add(va)
        self.failUnless('name' in obj)

    def test_call(self):
        obj = self._cut()
        va = self._view_action(_dummy_callable, 'name')
        obj['va'] = va
        self.assertEqual(len(tuple(obj('context', 'request'))), 1)
        self.assertEqual(obj('context', 'request'), ["contextrequest<betahaus.viewcomponent.ViewAction 'name'>"])

    def test_call_no_va(self):
        obj = self._cut()
        self.assertEqual(obj('context', 'request'), [])

    def test_context_vas_unrestricted(self):
        obj = self._cut()
        obj.add(self._view_action(_dummy_callable, 'hello'))
        obj.add(self._view_action(_dummy_callable, 'world'))
        res = tuple(obj.get_context_vas('context', 'request'))
        self.assertEqual(len(res), 2)

    def test_context_vas_special_permission(self):
        def _perm_checker(perm, context, request):
            """ Always say yes on text 'True'. """
            return perm == 'True'

        obj = self._cut(perm_checker = _perm_checker)
        obj.add(self._view_action(_dummy_callable, 'hello'))
        obj.add(self._view_action(_dummy_callable, 'cruel', permission = 'False'))
        obj.add(self._view_action(_dummy_callable, 'world', permission = 'True'))
        res = tuple(obj.get_context_vas('context', 'request'))
        self.assertEqual(len(res), 2)

    def test_context_vas_interface_required(self):
        obj = self._cut()
        obj.add(self._view_action(_dummy_callable, 'root_stuff', interface = contexts.IRoot))
        obj.add(self._view_action(_dummy_callable, 'more_root', interface = contexts.IRoot))
        obj.add(self._view_action(_dummy_callable, 'no_interface'))
        obj.add(self._view_action(_dummy_callable, 'organisation_stuff', interface = contexts.IOrganisation))
        obj.add(self._view_action(_dummy_callable, 'more_org', interface = contexts.IOrganisation))
        obj.add(self._view_action(_dummy_callable, 'even_more_org', interface = contexts.IOrganisation))
        #Root
        res = len(tuple(obj.get_context_vas(contexts.Root(), 'request')))
        self.assertEqual(res, 3)
        #Organisation
        res = len(tuple(obj.get_context_vas(contexts.Organisation(), 'request')))
        self.assertEqual(res, 4)
        #No iface
        res = len(tuple(obj.get_context_vas(testing.DummyResource(), 'request')))
        self.assertEqual(res, 1)

    def test_context_vas_containment(self):
        root = contexts.Root()
        org = contexts.Organisation()
        root['org'] = org
        obj = self._cut()
        obj.add(self._view_action(_dummy_callable, 'root_if', containment = contexts.IRoot))
        obj.add(self._view_action(_dummy_callable, 'root_cls', containment = contexts.Root))
        obj.add(self._view_action(_dummy_callable, 'org_if', containment = contexts.IOrganisation))
        obj.add(self._view_action(_dummy_callable, 'org_cls', containment = contexts.Organisation))
        obj.add(self._view_action(_dummy_callable, 'no_containment'))
        #Root
        res = len(tuple(obj.get_context_vas(root, 'request')))
        self.assertEqual(res, 3)
        #Organisation
        res = len(tuple(obj.get_context_vas(org, 'request')))
        self.assertEqual(res, 5)
        #No iface implemented by context
        res = len(tuple(obj.get_context_vas(testing.DummyResource(), 'request')))
        self.assertEqual(res, 1)        


class ViewActionTests(TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from betahaus.viewcomponent import ViewAction
        return ViewAction

    def test_callable(self):
        obj = self._cut(_dummy_callable, 'name')
        self.assertEqual(obj('hello', 'world'), "helloworld<betahaus.viewcomponent.ViewAction 'name'>")


class ViewActionDecoratorTests(TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_dummy_picked_up_on_scan(self):
        self.config.include("betahaus.viewcomponent.fixtures.dummy")
        util = self.config.registry.getUtility(IViewGroup, name = 'group')
        res = util('context', 'request')
        self.assertEqual(res, ["contextrequest<betahaus.viewcomponent.ViewAction 'action'>"])


class RenderViewGroupTests(TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from betahaus.viewcomponent import render_view_group
        return render_view_group

    def test_render_view_groups(self):
        request = testing.DummyRequest()
        context = testing.DummyResource()
        self.config.include("betahaus.viewcomponent.fixtures.dummy")
        res = self._fut(context, request, 'html')
        expected = "pyramid.testing.DummyResource, <class 'pyramid.testing.DummyRequest'>, <betahaus.viewcomponent.ViewAction 'stuff'>"
        self.assertEqual(res, expected)
