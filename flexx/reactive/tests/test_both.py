"""
Tests that should run in both Python and JS.
This helps ensure that both implementation work in the same way.

Focus on use-cases rather than coverage.

These tests work a bit awkward, but its very useful to be able to test
that the two systems work exactly the same way. You define a class with
signals, and then provide that class to a test function using a
decorator. The test function will then be run both in Python and in JS.
The test function should return an object, that when evaluates to a
string matches with the reference string given to the decorator. The
result string is made lowercase, and double quotes are converted to
single quotes.

"""

from pytest import raises
from flexx.util.testing import run_tests_if_main

from flexx.reactive import input, signal, react, source, HasSignals
from flexx.reactive.pyscript import create_js_signals_class, HasSignalsJS
from flexx.pyscript import js, evaljs, evalpy


def run_in_both(cls, reference, extra_classes=()):
    
    if reference.lower() != reference:
        raise ValueError('Test reference should be lowercase!')
    
    def wrapper(func):
        def runner():
            # Run in JS
            code = HasSignalsJS.jscode
            code += create_js_signals_class(cls, cls.__name__)
            for c in extra_classes:
                code += create_js_signals_class(c, c.__name__)
            code += 'var test = ' + js(func).jscode
            code += 'test(%s);' % cls.__name__
            jsresult = evaljs(code)
            jsresult = jsresult.replace('[ ', '[').replace(' ]', ']')
            jsresult = jsresult.replace('"', "'")
            print('js:', jsresult)
            # Run in Python
            pyresult = str(func(cls))
            pyresult = pyresult.replace('"', "'")
            print('py:', pyresult)
            #
            assert pyresult.lower() == reference
            assert jsresult.lower() == reference
        return runner
    return wrapper


class Name(HasSignals):
    
    _foo = 3
    _bar = 'bar'
    spam = [1, 2, 3]
    
    def __init__(self):
        self.r = []
        super().__init__()
    
    @input
    def first_name(v='john'):
        return str(v)
    
    @input
    def last_name(v='doe'):
        return str(v)
    
    @signal('first_name', 'last_name')
    def full_name(self, n1, n2):
        self.r.append('')
        return n1 + ' ' + n2

@run_in_both(Name, "['', 'john doe', '', 'almar klein', '', 'jorik klein']")
def test_pull(Name):
    name = Name()
    name.r.append(name.full_name())
    name.first_name('almar')
    name.last_name('klein')
    name.r.append(name.full_name())
    name.first_name('jorik')
    name.r.append(name.full_name())
    return name.r

@run_in_both(Name, "['', 'john doe', '', 'jane doe']")
def test_disconnecting_signal(Name):
    s = Name()
    s.r.append(s.full_name())
    
    # Disconnect, but because its a react signal, it re-connects at once
    s.full_name.disconnect()
    s.first_name('almar')
    s.first_name('jorik')
    s.first_name('jane')
    
    s.r.append(s.full_name())  # connects now
    
    return s.r  

@run_in_both(Name, "[true, true, '', true, true, true, true, '', true, true]")
def test_signal_attributes(Name):
    s = Name()
    s.r.append(s.full_name._timestamp == 0)
    s.r.append(s.full_name._value is None)
    s.full_name()
    s.r.append(s.full_name._timestamp > 0)
    s.r.append(s.full_name._last_timestamp == 0)
    s.r.append(s.full_name._value == 'john doe')
    s.r.append(s.full_name._last_value is None)
    s.first_name('jane')
    s.full_name()
    s.r.append(s.full_name._last_timestamp > 0)
    s.r.append(s.full_name._last_value == 'john doe')
    return s.r

@run_in_both(Name, "[3, 'bar', [1, 2, 3], 2, 'err', 'err']")
def test_hassignal_attributes(Name):
    s = Name()
    # class attributes
    s.r.append(s._foo)
    s.r.append(s._bar)
    s.r.append(s.spam)
    # can set other attributes
    s.eggs = 2
    s.r.append(s.eggs)
    # cannot overwrite signals
    try:
        s.first_name = 2
        s.r.append(s.first_name)
    except Exception:
        s.r.append('err')
    # cannot overwrite signal attributes
    try:
        s.first_name.value = 2
        s.r.append(s.first_name.value)
    except Exception:
        s.r.append('err')
    return s.r

@run_in_both(Name, "['first_name', 'full_name', 'last_name']")
def test_hassignal__signals__(Name):
    s = Name()
    return s.__signals__


class Title(HasSignals):
    
    def __init__(self):
        self.r = []
        super().__init__()
    
    @input
    def title(v=''):
        return v
    
    @signal('title')
    def title_len(v):
        return len(v)
    
    @react('title_len')
    def show_title(self, v):
        self.r.append(v)

@run_in_both(Title, '[0, 2, 4, false]')
def test_push(Title):
    foo = Title()
    foo.title('xx')
    foo.title('xxxx')
    foo.r.append(foo.show_title.not_connected)
    return foo.r

@run_in_both(Title, "[0, 0, 2]")
def test_disconnecting_react(Title):
    s = Title()
    
    # Disconnect, but because its a react signal, it re-connects at once
    s.show_title.disconnect()
    s.title('xx')
    
    return s.r


class Unconnected(HasSignals):
    
    @input
    def s0(v=''):
        return v
    
    @signal('nope')
    def s1(v):
        return v
    
    @signal('button.title')
    def s2(v):
        return v
    
    @signal('s2')
    def s3(v):
        return v
    
    @react('s3')
    def s4(v):
        return v

@run_in_both(Unconnected, "[false, true, 'signal 'button.title' does not exist.']")
def test_unconnected(Cls):
    s = Cls()
    r = []
    r.append(bool(s.s0.not_connected))
    r.append(bool(s.s1.not_connected))
    r.append(s.s2.not_connected)
    return r

@run_in_both(Unconnected, "[true, false, 'err2', 'err3', 'err4']")
def test_unconnected_handling(Cls):
    s = Cls()
    r = []
    r.append(bool(s.s2.not_connected))
    r.append(bool(s.s3.not_connected))
    #
    try:
        s.s2()
    except Exception:
        r.append('err2')  # error, because this signal is not connected
    try:
        s.s3()
    except Exception:
        r.append('err3')  # error, because an upstream signal is not connected
    try:
        s.s4()
    except Exception:
        r.append('err4')  # error, because an upstream signal is not connected
    return r

@run_in_both(Unconnected, "['ha', 'ho', 'err4']", extra_classes=(Title,))
def test_unconnected_connect(Cls):
    s = Cls()
    r = []
    # We add an object named 'button' with signal 'title', exactly what s2 needs
    button = Title()
    s.button = button
    button.title('ha')
    # Now by just calling s4, s2 will connect
    r.append(s.s4())
    
    # Now we remove 'button'
    del s.button
    # This should still work, since connections are in place
    button.title('ho')
    r.append(s.s4())
    
    # And we break connections
    s.s2.disconnect()
    try:
        s.s4()
    except Exception:
        r.append('err4')  # error, because an upstream signal is not connected
    
    return r


class SignalTypes(HasSignals):
    
    @input
    def s1(v):
        return v
    
    @source
    def s2(v):
        return v
    
    @signal('s2')
    def s3(v):
        return v
    
    @react('s2')
    def s4(v):
        return v

@run_in_both(SignalTypes, "['s2', 's3', 's4', 's3', 's4']")
def test_setting_inputs(Cls):
    s = Cls()
    r = []
    # These do not error
    s.s1('foo')
    s.s1._set('foo')
    s.s2._set('foo')
    # But these do
    try:
        s.s2('foo')
    except Exception:
        r.append('s2')
    try:
        s.s3('foo')
    except Exception:
        r.append('s3')
    try:
        s.s4('foo')
    except Exception:
        r.append('s4')
    # And these too
    try:
        s.s3._set('foo')
    except Exception:
        r.append('s3')
    try:
        s.s4._set('foo')
    except Exception:
        r.append('s4')
    return r

@run_in_both(SignalTypes, "[true, 'foo', 'bar']")
def test_setting_inputs2(Cls):
    s = Cls()
    r = []
    r.append(s.s1() is None)  # test no default value
    s.s1('foo')
    s.s2._set('bar')
    r.append(s.s1())
    r.append(s.s2())
    return r


class Circular(HasSignals):
    
    @input('s3')
    def s1(v1=10, v3=None):
        if v3 is None:
            return v1
        else:
            return v3 + 1
    
    @signal('s1')
    def s2(v):
        return v + 1
    
    @signal('s2')
    def s3(v):
        return v + 1

@run_in_both(Circular, "[10, 11, 12, '', 2, 3, 4]")
def test_circular(Cls):
    s = Cls()
    r = []
    r.append(s.s1())
    r.append(s.s2())
    r.append(s.s3())
    r.append('')
    s.s1(2)
    r.append(s.s1())
    r.append(s.s2())
    r.append(s.s3())
    return r


class Temperature(HasSignals):  # to avoid round erros, the relation is simplified
    @input('f')
    def c(v=32, f=None):
        if f is None:
            return int(v)
        else:
            return f - 32
    
    @input('c')
    def f(v=0, c=None):
        if c is None:
            return int(v)
        else:
            return c + 32

@run_in_both(Temperature, "[32, 0, '', 10, 42, '', -22, 10]")
def test_circular_temperature(Cls):
    s = Cls()
    r = []
    r.append(s.c())
    r.append(s.f())
    r.append('')
    s.c(10)
    r.append(s.c())
    r.append(s.f())
    r.append('')
    s.f(10)
    r.append(s.c())
    r.append(s.f())
    return r




run_tests_if_main()