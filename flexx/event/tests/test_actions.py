"""
Test actions.
"""

from flexx.util.testing import run_tests_if_main, skipif, skip, raises
from flexx.event._both_tester import run_in_both, this_is_js

from flexx import event

loop = event.loop


class MyObject(event.Component):
    
    foo = event.Property()
    
    @event.action
    def set_foo(self, v):
        self._mutate_foo(v)
    
    @event.action
    def set_foo_add(self, *args):
        self._mutate_foo(sum(args))
    
    @event.action
    def do_silly(self):
        return 1  # not allowed


@run_in_both(MyObject)
def test_action_simple():
    """
    True
    True
    hi
    hi
    43
    43
    12
    ? not supposed to return a value
    """
    
    m = MyObject()
    print(m.foo is None)  # None is represented as "null" in JS
    
    m.set_foo("hi")
    print(m.foo is None)
    loop.iter()
    print(m.foo)
    
    m.set_foo(42)
    m.set_foo(43)
    print(m.foo)
    loop.iter()
    print(m.foo)
    
    m.set_foo_add(3, 4, 5)
    print(m.foo)
    loop.iter()
    print(m.foo)
    
    m.do_silly()
    loop.iter()


# todo: need kwargs in js!
@run_in_both(MyObject, js=False)
def test_action_init():
    """
    True
    9
    True
    42
    """
    
    m = MyObject(foo=9)
    print(m.foo is None)
    loop.iter()
    print(m.foo)
    
    m = MyObject(foo=9)
    print(m.foo is None)
    m.set_foo(42)
    loop.iter()
    print(m.foo)


class MyObject_autoaction(event.Component):
    
    foo = event.Property(settable=True)


@run_in_both(MyObject_autoaction)
def test_action_auto():
    """
    True
    True
    hi
    """
    
    m = MyObject_autoaction()
    print(m.foo is None)  # None is represented as "null" in JS
    
    m.set_foo("hi")
    print(m.foo is None)
    loop.iter()
    print(m.foo)


class MyObject_actionclash1(event.Component):
    
    foo = event.Property(settable=True)
    
    @event.action
    def set_foo(self, v):
        print('Custom one')
        self._mutate_foo(v)


class MyObject_actionclash2(MyObject_autoaction):
    
    @event.action
    def set_foo(self, v):
        print('Custom one')
        self._mutate_foo(v)


@run_in_both(MyObject_actionclash1, MyObject_actionclash2)
def test_action_clash():
    """
    Custom one
    hi
    Custom one
    hi
    """
    
    m = MyObject_actionclash1()
    m.set_foo("hi")
    loop.iter()
    print(m.foo)
    
    m = MyObject_actionclash2()
    m.set_foo("hi")
    loop.iter()
    print(m.foo)


class MyObject2(MyObject):
    
    @event.action
    def set_foo(self, v):
        super().set_foo(v + 1)


class MyObject3(MyObject_autoaction):  # base class has autogenerated set_foo
    
    @event.action
    def set_foo(self, v):
        super().set_foo(v + 1)


@run_in_both(MyObject2, MyObject3)
def test_action_inheritance():
    """
    5
    5
    """
    m = MyObject2()
    m.set_foo(4)
    loop.iter()
    print(m.foo)
    
    m = MyObject3()
    m.set_foo(4)
    loop.iter()
    print(m.foo)


## Meta-ish tests that are similar for property/emitter/action/reaction


@run_in_both(MyObject)
def test_action_not_settable():
    """
    fail AttributeError
    """
    
    m = MyObject()
    
    try:
        m.set_foo = 3
    except AttributeError:
        print('fail AttributeError')
    
    # We cannot prevent deletion in JS, otherwise we cannot overload


def test_action_python_only():
    
    m = MyObject()
    
    # Action decorator needs proper callable
    with raises(TypeError):
        event.action(3)
    with raises(RuntimeError):
        event.action(isinstance)
    
    # Check type of the instance attribute
    assert isinstance(m.set_foo, event._action.Action)
    
    # Cannot set or delete an action
    with raises(AttributeError):
        m.set_foo = 3
    with raises(AttributeError):
        del m.set_foo
    
    # Repr and docs
    assert 'action' in repr(m.__class__.set_foo).lower()
    assert 'action' in repr(m.set_foo).lower()
    assert 'foo' in repr(m.set_foo)
    # Also for autogenereated action
    m = MyObject_autoaction()
    assert 'action' in repr(m.__class__.set_foo).lower()
    assert 'action' in repr(m.set_foo).lower()
    assert 'foo' in repr(m.set_foo)


run_tests_if_main()
