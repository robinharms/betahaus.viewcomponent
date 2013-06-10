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

def _name_callable(context, request, va):
    return va.name

def _bad_callable(*args):
    return

def _failing_callable(*args):
    raise Exception('Buhu!')


class ViewGroupTests(TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from betahaus.viewcomponent.models import ViewGroup
        return ViewGroup

    @property
    def _view_action(self):
        from betahaus.viewcomponent.models import ViewAction
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

    def test_del(self):
        obj = self._cut()
        va = self._view_action(_dummy_callable, 'name')
        obj.add(va)
        self.failUnless('name' in obj) #To make sure
        del obj['name']
        self.failIf('name' in obj)

    def test_len(self):
        obj = self._cut()
        va = self._view_action(_dummy_callable, 'name')
        obj.add(va)
        self.assertEqual(len(obj), 1)

    def test_call(self):
        obj = self._cut()
        va = self._view_action(_dummy_callable, 'name')
        obj['va'] = va
        self.assertEqual(obj('context', 'request'), "contextrequest<betahaus.viewcomponent.models.ViewAction 'name'>")

    def test_call_no_va(self):
        obj = self._cut()
        self.assertEqual(obj('context', 'request'), '')

    def test_call_bad_output_from_va(self):
        obj = self._cut()
        va = self._view_action(_bad_callable, 'name')
        obj.add(va)
        self.assertRaises(TypeError, obj, None, None)

    def test_call_exception_from_va(self):
        obj = self._cut()
        va = self._view_action(_failing_callable, 'this_view_group')
        obj.add(va)
        try:
            obj(None, None)
        except Exception, exc:
            self.failUnless('this_view_group' in exc.args[0])

    def test_default_order(self):
        obj = self._cut()
        obj.add(self._view_action(_dummy_callable, 'one'))
        obj.add(self._view_action(_dummy_callable, 'two'))
        self.assertEqual(obj.order, ['one', 'two'])
        
    def test_set_order(self):
        obj = self._cut()
        obj.add(self._view_action(_dummy_callable, 'one'))
        obj.add(self._view_action(_dummy_callable, 'two'))
        obj.order = ['two', 'one']
        self.assertEqual(obj.order, ['two', 'one'])

    def test_order_respected_on_call(self):
        obj = self._cut()
        obj.add(self._view_action(_name_callable, 'one'))
        obj.add(self._view_action(_name_callable, 'two'))
        obj.order = ['two', 'one']
        context = None
        request = None
        self.assertEqual(obj(context, request), 'twoone')

    def test_order_bad_key(self):
        obj = self._cut()
        try:
            obj.order = ['404']
            self.fail("KeyError not raised")
        except KeyError:
            pass

    def test_set_order_with_some_keys_left_out(self):
        obj = self._cut()
        obj.add(self._view_action(_name_callable, 'one'))
        obj.add(self._view_action(_name_callable, 'two'))
        obj.order = ['two']
        #one should be appended as well
        self.assertEqual(obj.order, ['two', 'one'])

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

    def test_get(self):
        obj = self._cut()
        va = self._view_action(_dummy_callable, 'hello')
        obj.add(va)
        self.assertEqual(obj.get('hello'), va)

    def test_keys_respect_order(self):
        obj = self._cut()
        obj.add(self._view_action(_name_callable, 'one'))
        obj.add(self._view_action(_name_callable, 'two'))
        obj.add(self._view_action(_name_callable, 'three'))
        obj.order = ['three', 'one']
        self.assertEqual(obj.keys(), ['three', 'one', 'two'])

    def test_values_respect_order(self):
        obj = self._cut()
        va1 = self._view_action(_name_callable, 'one')
        va2 = self._view_action(_name_callable, 'two')
        va3 = self._view_action(_name_callable, 'three')
        obj.add(va1)
        obj.add(va2)
        obj.add(va3)
        obj.order = ['three', 'one']
        self.assertEqual(obj.values(), [va3, va1, va2])

    def test_items_respect_order(self):
        obj = self._cut()
        va1 = self._view_action(_name_callable, 'one')
        va2 = self._view_action(_name_callable, 'two')
        va3 = self._view_action(_name_callable, 'three')
        obj.add(va1)
        obj.add(va2)
        obj.add(va3)
        obj.order = ['three', 'one']
        self.assertEqual(obj.items(), [('three', va3), ('one', va1), ('two', va2)])


class ViewActionTests(TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from betahaus.viewcomponent.models import ViewAction
        return ViewAction

    def test_callable(self):
        obj = self._cut(_dummy_callable, 'name')
        self.assertEqual(obj('hello', 'world'), "helloworld<betahaus.viewcomponent.models.ViewAction 'name'>")


class ViewActionDecoratorTests(TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_dummy_picked_up_on_scan(self):
        self.config.include("betahaus.viewcomponent.fixtures.dummy")
        util = self.config.registry.getUtility(IViewGroup, name = 'group')
        res = util('context', 'request')
        self.assertEqual(res, "contextrequest<betahaus.viewcomponent.models.ViewAction 'action'>")


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
        expected = "{}, {}, <betahaus.viewcomponent.models.ViewAction 'stuff'>".format(
            testing.DummyResource, testing.DummyRequest)
        self.assertEqual(res, expected)


class RenderViewActionTests(TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from betahaus.viewcomponent import render_view_action
        return render_view_action

    def test_render_view_action(self):
        request = testing.DummyRequest()
        context = testing.DummyResource()
        self.config.include("betahaus.viewcomponent.fixtures.group")
        res = self._fut(context, request, 'group', 'one')
        expected = "one"
        self.assertEqual(res, expected)
