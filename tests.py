from collections import namedtuple
import ast
import pytest
import tempfile
import subprocess
import shlex
import os.path
from pathlib import Path

from py3line import to_tokens, get_names, Py3LineSyntaxError

Py3LineCase = lambda *args, full_check=True, code=0: namedtuple('Py3LineCase', 'actions, input, output, full_check, code')(*args, full_check, code)
PyCodeCase = lambda *args, assert_get_names=None: namedtuple('PyCodePy3LineCase', 'code, exception, tokens, assert_get_names')(*args, assert_get_names)
PY3LINE = './py3line.py'
ROOT = Path(os.path.dirname(__file__))

PY3LINE_TESTS = [
    Py3LineCase(
        ['print(line)'], 
        list(map(str, range(100))),
        list(map(str, range(100)))),
    Py3LineCase(
        ['print(None)'], 
        list(map(str, range(100))),
        ['None']),
    Py3LineCase(
        ['print(sys)'], 
        list(map(str, range(100))),
        ["<module 'sys' (built-in)>"]),
    Py3LineCase(
        ['x = line.split()', 'y = len(x[0])', 'print(y, *x[1:])'], 
        ['xxxx hello', 'xx hi'], 
        ['4 hello', '2 hi']),
    Py3LineCase(
        ['x = line.split()', 'line = len(x[0])', 's = sum(stream)', 'print(s)'], 
        ['xxxx hello', 'xx hi'], 
        ['6']),
    Py3LineCase(
        "print(len(line.split()))".split(';'),
        "Here are\nsome\nwords for you.".split('\n'),
        "2\n1\n3".split('\n')),
    # echo -e "Here are\nsome\nwords for you." | ./py3line.py "x = len(line.split(' ')); print(x, line)"
    Py3LineCase(
        "x = len(line.split()); print(x, line)".split(';'),
        "Here are\nsome\nwords for you.".split('\n'),
        "2 Here are\n1 some\n3 words for you.".split('\n')),
    # echo -e "Here are\nsome\nwords for you." | ./py3line.py "line = len(line.split()); print(sum(stream))"
    Py3LineCase(
        "line = len(line.split()); print(sum(stream))".split(';'),
        "Here are\nsome\nwords for you.".split('\n'),
        "6".split('\n')),
    # echo -e "Here are\nsome\nwords for you." | ./py3line.py "line = len(line.split()); print(sum(stream), max(stream))"
    Py3LineCase(
        "line = len(line.split()); print(sum(stream), max(stream))".split(';'),
        "Here are\nsome\nwords for you.".split('\n'),
        "    stream = transform2(process1(stream))\n    print(sum(stream), max(stream))\nValueError: max() arg is an empty sequence".split('\n'),
        full_check=False, code=1),
    # echo -e "Here are\nsome\nwords for you." | ./py3line.py "line = len(line.split()); stream = list(stream); print(sum(stream), max(stream))"
    Py3LineCase(
        "line = len(line.split()); stream = list(stream); print(sum(stream), max(stream))".split(';'),
        "Here are\nsome\nwords for you.".split('\n'),
        "6 3".split('\n')),
    # echo -e "Here are\nsome\nwords for you." | ./py3line.py "s = 0; m = 0; num_of_words = len(line.split()); s += num_of_words; m = max(m, num_of_words); print(s, m)"
    Py3LineCase(
        "s = 0; m = 0; num_of_words = len(line.split()); s += num_of_words; m = max(m, num_of_words); print(s, m)".split(';'),
        "Here are\nsome\nwords for you.".split('\n'),
        "2 2\n3 2\n6 3".split('\n')),
    # echo -e "Here are\nsome\nwords for you." | ./py3line.py "s = 0; m = 0; num_of_words = len(line.split()); s += num_of_words; m = max(m, num_of_words); for line in stream: pass; print(s, m)"
    Py3LineCase(
        "s = 0; m = 0; num_of_words = len(line.split()); s += num_of_words; m = max(m, num_of_words); for line in stream: pass; print(s, m)".split(';'),
        "Here are\nsome\nwords for you.".split('\n'),
        "6 3".split('\n')),
    # echo -e "Here are\nsome\nwords for you." | ./py3line.py "for line in stream: print(1); for line in stream: print(1)"
    Py3LineCase(
        "for line in stream: print(1); for line in stream: print(1)".split(';'),
        "Here are\nsome\nwords for you.".split('\n'),
        "1\n1\n1".split('\n')),
    Py3LineCase(
        "print(2); for line in stream: print(1); print(88); for line in stream: print(1); print(999)".split(';'),
        "Here are\nsome\nwords for you.".split('\n'),
        "2\n1\n1\n1\n88\n999".split('\n')),
    Py3LineCase(
        "print(2); list(stream); for line in stream: print(1); print(88); for line in stream: print(1); print(999)".split(';'),
        "Here are\nsome\nwords for you.".split('\n'),
        "2\n88\n999".split('\n')),

    # cat ./testsuit/test.txt | ./py3line.py
    Py3LineCase(
        [],
        (ROOT/'testsuit'/'test.txt').open().read().split('\n'),
        ['']),
    Py3LineCase(
        [],
        (ROOT/'testsuit'/'test.txt').open().read().split('\n'),
        ['']),
    Py3LineCase(
        [''],
        (ROOT/'testsuit'/'test.txt').open().read().split('\n'),
        ['']),
    Py3LineCase(
        ['', '', ''],
        (ROOT/'testsuit'/'test.txt').open().read().split('\n'),
        ['']),

    # cat ./testsuit/test.txt | ./py3line.py "stream = enumerate(stream); print(line)"
    Py3LineCase(
        "stream = enumerate(stream); print(line)".split(';'),
        (ROOT/'testsuit'/'test.txt').open().read().split('\n'),
        "(0, 'This is my cat,')\n(1, ' whose name is Betty.')\n(2, 'This is my dog,')\n(3, ' whose name is Frank.')\n(4, 'This is my fish,')\n(5, ' whose name is George.')\n(6, 'This is my goat,')\n(7, ' whose name is Adam.')".split('\n')),
    # cat ./testsuit/test.txt | ./py3line.py "stream = enumerate(stream); print(line[0], line[1])"
    Py3LineCase(
        "stream = enumerate(stream); print(line[0], line[1])".split(';'),
        (ROOT/'testsuit'/'test.txt').open().read().split('\n'),
        "0 This is my cat,\n1  whose name is Betty.\n2 This is my dog,\n3  whose name is Frank.\n4 This is my fish,\n5  whose name is George.\n6 This is my goat,\n7  whose name is Adam.".split('\n')),
    # cat ./testsuit/test.txt | ./py3line.py "stream = enumerate(stream); print(*line)"
    Py3LineCase(
        "stream = enumerate(stream); print(*line)".split(';'),
        (ROOT/'testsuit'/'test.txt').open().read().split('\n'),
        "0 This is my cat,\n1  whose name is Betty.\n2 This is my dog,\n3  whose name is Frank.\n4 This is my fish,\n5  whose name is George.\n6 This is my goat,\n7  whose name is Adam.".split('\n')),
    # cat ./testsuit/test.txt | ./py3line.py "s = line.split(); print(s[0], s[-1])"
    Py3LineCase(
        "s = line.split(); print(s[0], s[-1])".split(';'),
        (ROOT/'testsuit'/'test.txt').open().read().split('\n'),
        "This cat,\nwhose Betty.\nThis dog,\nwhose Frank.\nThis fish,\nwhose George.\nThis goat,\nwhose Adam.".split('\n')),

]

PYCODE_TESTS = [
    # ("Expressions")
    PyCodeCase('2', None, "Expr(value=Num(n=2))", assert_get_names=(set(), set(), set())),
    PyCodeCase('-2.2', None, "Expr(value=UnaryOp(op=USub(), operand=Num(n=2.2)))"),
    PyCodeCase('"2"', None, "Expr(value=Str(s='2'))"),
    PyCodeCase('b"2"', None, "Expr(value=Bytes(s=b'2'))"),
    PyCodeCase('f"sin({a}) is {sin(a):.3}"', SyntaxError, "Expr(value=JoinedStr(values=[Str(s='sin('), FormattedValue(value=Name(id='a', ctx=Load()), conversion=-1, format_spec=None), Str(s=') is '), FormattedValue(value=Call(func=Name(id='sin', ctx=Load()), args=[Name(id='a', ctx=Load())], keywords=[]), conversion=-1, format_spec=JoinedStr(values=[Str(s='.3')]))]))"),
    PyCodeCase(r'r"\n"', None, r"Expr(value=Str(s='\\n'))"),
    PyCodeCase('[]', None, "Expr(value=List(elts=[], ctx=Load()))"),
    PyCodeCase('[1]', None, "Expr(value=List(elts=[Num(n=1)], ctx=Load()))"),
    PyCodeCase(',', SyntaxError, ""),
    PyCodeCase('(,)', SyntaxError, ""),
    PyCodeCase('1,', None, "Expr(value=Tuple(elts=[Num(n=1)], ctx=Load()))"),
    PyCodeCase('(1,)', None, "Expr(value=Tuple(elts=[Num(n=1)], ctx=Load()))"),
    PyCodeCase('{1,}', None, "Expr(value=Set(elts=[Num(n=1)]))"),
    PyCodeCase('{1}', None, "Expr(value=Set(elts=[Num(n=1)]))"),
    PyCodeCase('{}', None, "Expr(value=Dict(keys=[], values=[]))"),
    PyCodeCase('{"f":1}', None, "Expr(value=Dict(keys=[Str(s='f')], values=[Num(n=1)]))"),
    PyCodeCase('...', None, "Expr(value=Ellipsis())", assert_get_names=(set(), set(), set())),
    PyCodeCase('None', None, "Expr(value=NameConstant(value=None))", assert_get_names=(set(), set(), set())),
    PyCodeCase('True', None, "Expr(value=NameConstant(value=True))", assert_get_names=(set(), set(), set())),
    PyCodeCase('False', None, "Expr(value=NameConstant(value=False))", assert_get_names=(set(), set(), set())),
    PyCodeCase('-b', None, "Expr(value=UnaryOp(op=USub(), operand=Name(id='b', ctx=Load())))", assert_get_names=(set(), {'b'}, set())),
    PyCodeCase('c in d', None, "Expr(value=Compare(left=Name(id='c', ctx=Load()), ops=[In()], comparators=[Name(id='d', ctx=Load())]))", assert_get_names=(set(), {'c', 'd'}, set())),
    PyCodeCase('e not in f', None, "Expr(value=Compare(left=Name(id='e', ctx=Load()), ops=[NotIn()], comparators=[Name(id='f', ctx=Load())]))"),
    PyCodeCase('g is h', None, "Expr(value=Compare(left=Name(id='g', ctx=Load()), ops=[Is()], comparators=[Name(id='h', ctx=Load())]))"),
    PyCodeCase('j == 7', None, "Expr(value=Compare(left=Name(id='j', ctx=Load()), ops=[Eq()], comparators=[Num(n=7)]))"),
    PyCodeCase('0 < k < 7', None, "Expr(value=Compare(left=Num(n=0), ops=[Lt(), Lt()], comparators=[Name(id='k', ctx=Load()), Num(n=7)]))", assert_get_names=(set(), {'k'}, set())),
    PyCodeCase('l if m else n + 1', None, "Expr(value=IfExp(test=Name(id='m', ctx=Load()), body=Name(id='l', ctx=Load()), orelse=BinOp(left=Name(id='n', ctx=Load()), op=Add(), right=Num(n=1))))", assert_get_names=(set(), {'l', 'm', 'n'}, set())),
    PyCodeCase('print(s)', None, "Expr(value=Call(func=Name(id='print', ctx=Load()), args=[Name(id='s', ctx=Load())], keywords=[]))", assert_get_names=(set(), {'print', 's'}, set())),
    PyCodeCase('func(p, q=r, *s, **t)', None, "Expr(value=Call(func=Name(id='func', ctx=Load()), args=[Name(id='p', ctx=Load()), Starred(value=Name(id='s', ctx=Load()), ctx=Load())], keywords=[keyword(arg='q', value=Name(id='r', ctx=Load())), keyword(arg=None, value=Name(id='t', ctx=Load()))]))", assert_get_names=(set(), {'p', 'r', 's', 't', 'func'}, set())),
    PyCodeCase('u.v', None, "Expr(value=Attribute(value=Name(id='u', ctx=Load()), attr='v', ctx=Load()))", assert_get_names=(set(), {'u'}, set())),
    PyCodeCase('w[3]', None, "Expr(value=Subscript(value=Name(id='w', ctx=Load()), slice=Index(value=Num(n=3)), ctx=Load()))", assert_get_names=(set(), {'w'}, set())),
    PyCodeCase('x[y]', None, "Expr(value=Subscript(value=Name(id='x', ctx=Load()), slice=Index(value=Name(id='y', ctx=Load())), ctx=Load()))", assert_get_names=(set(), {'x', 'y'}, set())),
    PyCodeCase('z["dd"]', None, "Expr(value=Subscript(value=Name(id='z', ctx=Load()), slice=Index(value=Str(s='dd')), ctx=Load()))", assert_get_names=(set(), {'z'}, set())),
    PyCodeCase('l1[1:2]', None, "Expr(value=Subscript(value=Name(id='l1', ctx=Load()), slice=Slice(lower=Num(n=1), upper=Num(n=2), step=None), ctx=Load()))", assert_get_names=(set(), {'l1'}, set())),
    PyCodeCase('l2[1:2, 3]', None, "Expr(value=Subscript(value=Name(id='l2', ctx=Load()), slice=ExtSlice(dims=[Slice(lower=Num(n=1), upper=Num(n=2), step=None), Index(value=Num(n=3))]), ctx=Load()))", assert_get_names=(set(), {'l2'}, set())),
    PyCodeCase('k for x in stream', SyntaxError, ""),
    PyCodeCase('(k1 for x1 in stream)', None, "Expr(value=GeneratorExp(elt=Name(id='k1', ctx=Load()), generators=[comprehension(target=Name(id='x1', ctx=Store()), iter=Name(id='stream', ctx=Load()), ifs=[])]))", assert_get_names=(set(), {'k1', 'stream'}, {'x1'})),
    PyCodeCase('[k2 for x2 in stream]', None, "Expr(value=ListComp(elt=Name(id='k2', ctx=Load()), generators=[comprehension(target=Name(id='x2', ctx=Store()), iter=Name(id='stream', ctx=Load()), ifs=[])]))", assert_get_names=(set(), {'k2', 'stream'}, {'x2'})),
    PyCodeCase('(k3 for x3 in stream for k in x if k)', None, "Expr(value=GeneratorExp(elt=Name(id='k3', ctx=Load()), generators=[comprehension(target=Name(id='x3', ctx=Store()), iter=Name(id='stream', ctx=Load()), ifs=[]), comprehension(target=Name(id='k', ctx=Store()), iter=Name(id='x', ctx=Load()), ifs=[Name(id='k', ctx=Load())])]))", assert_get_names=(set(), {'k3', 'stream', 'k', 'x'}, {'x3', 'k'})),
    PyCodeCase('[k4 for x4 in stream for k in x if k]', None, "Expr(value=ListComp(elt=Name(id='k4', ctx=Load()), generators=[comprehension(target=Name(id='x4', ctx=Store()), iter=Name(id='stream', ctx=Load()), ifs=[]), comprehension(target=Name(id='k', ctx=Store()), iter=Name(id='x', ctx=Load()), ifs=[Name(id='k', ctx=Load())])]))", assert_get_names=(set(), {'k4', 'stream', 'k', 'x'}, {'x4', 'k'})),
    PyCodeCase('lambda x: x + 1', None, "Expr(value=Lambda(args=arguments(args=[arg(arg='x', annotation=None)], vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]), body=BinOp(left=Name(id='x', ctx=Load()), op=Add(), right=Num(n=1))))", assert_get_names=(set(), {'x'}, {'x'})),
    PyCodeCase('lambda b=1, c=2, *d, f=z1, **e: z2', None, "Expr(value=Lambda(args=arguments(args=[arg(arg='b', annotation=None), arg(arg='c', annotation=None)], vararg=arg(arg='d', annotation=None), kwonlyargs=[arg(arg='f', annotation=None)], kw_defaults=[Name(id='z1', ctx=Load())], kwarg=arg(arg='e', annotation=None), defaults=[Num(n=1), Num(n=2)]), body=Name(id='z2', ctx=Load())))", assert_get_names=(set(), {'z1', 'z2'}, {'b', 'c', 'd', 'e', 'f'})),
    PyCodeCase('lambda b=1, c=2, *d, m, f=3, **g: e + g', None, "Expr(value=Lambda(args=arguments(args=[arg(arg='b', annotation=None), arg(arg='c', annotation=None)], vararg=arg(arg='d', annotation=None), kwonlyargs=[arg(arg='m', annotation=None), arg(arg='f', annotation=None)], kw_defaults=[None, Num(n=3)], kwarg=arg(arg='g', annotation=None), defaults=[Num(n=1), Num(n=2)]), body=BinOp(left=Name(id='e', ctx=Load()), op=Add(), right=Name(id='g', ctx=Load()))))", assert_get_names=(set(), {'e', 'g'}, {'b', 'c', 'd', 'm', 'f', 'g'})),
    PyCodeCase('yield x', None, "Expr(value=Yield(value=Name(id='x', ctx=Load())))", assert_get_names=(set(), {'x'}, set())),
    PyCodeCase('yield from x', None, "Expr(value=YieldFrom(value=Name(id='x', ctx=Load())))", assert_get_names=(set(), {'x'}, set())),
    PyCodeCase('await x', SyntaxError, ""),

    # ("Statements")
    PyCodeCase('lam = lambda b=1, c=2, *d, m, f=3, **g: e + g', None, "Assign(targets=[Name(id='lam', ctx=Store())], value=Lambda(args=arguments(args=[arg(arg='b', annotation=None), arg(arg='c', annotation=None)], vararg=arg(arg='d', annotation=None), kwonlyargs=[arg(arg='m', annotation=None), arg(arg='f', annotation=None)], kw_defaults=[None, Num(n=3)], kwarg=arg(arg='g', annotation=None), defaults=[Num(n=1), Num(n=2)]), body=BinOp(left=Name(id='e', ctx=Load()), op=Add(), right=Name(id='g', ctx=Load()))))", assert_get_names=({'lam'}, {'e', 'g'}, {'b', 'c', 'd', 'm', 'f', 'g'})),
    PyCodeCase('gen = (k1 for x1 in stream)', None, "Assign(targets=[Name(id='gen', ctx=Store())], value=GeneratorExp(elt=Name(id='k1', ctx=Load()), generators=[comprehension(target=Name(id='x1', ctx=Store()), iter=Name(id='stream', ctx=Load()), ifs=[])]))", assert_get_names=({'gen'}, {'k1', 'stream'}, {'x1'})),
    PyCodeCase('variable = 7', None, "Assign(targets=[Name(id='variable', ctx=Store())], value=Num(n=7))", assert_get_names=({'variable'}, set(), set())),
    PyCodeCase('variable = var2', None, "Assign(targets=[Name(id='variable', ctx=Store())], value=Name(id='var2', ctx=Load()))", assert_get_names=({'variable'}, {'var2'}, set())),
    PyCodeCase('variable = var2 = v3 = 9', None, "Assign(targets=[Name(id='variable', ctx=Store()), Name(id='var2', ctx=Store()), Name(id='v3', ctx=Store())], value=Num(n=9))", assert_get_names=({'variable', 'var2', 'v3'}, set(), set())),
    PyCodeCase('variable = (va2, va3) = v3 = (10, 11)', None, "Assign(targets=[Name(id='variable', ctx=Store()), Tuple(elts=[Name(id='va2', ctx=Store()), Name(id='va3', ctx=Store())], ctx=Store()), Name(id='v3', ctx=Store())], value=Tuple(elts=[Num(n=10), Num(n=11)], ctx=Load()))", assert_get_names=({'variable', 'va2', 'v3', 'va3'}, set(), set())),
    PyCodeCase('q, w = 7, 8', None, "Assign(targets=[Tuple(elts=[Name(id='q', ctx=Store()), Name(id='w', ctx=Store())], ctx=Store())], value=Tuple(elts=[Num(n=7), Num(n=8)], ctx=Load()))", assert_get_names=({'q', 'w'}, set(), set())),
    PyCodeCase('a, *b = it', None, "Assign(targets=[Tuple(elts=[Name(id='a', ctx=Store()), Starred(value=Name(id='b', ctx=Store()), ctx=Store())], ctx=Store())], value=Name(id='it', ctx=Load()))", assert_get_names=({'a', 'b'}, {'it'}, set())),
    PyCodeCase('a, ((c0, k2), c1, *b) = it', None, "Assign(targets=[Tuple(elts=[Name(id='a', ctx=Store()), Tuple(elts=[Tuple(elts=[Name(id='c0', ctx=Store()), Name(id='k2', ctx=Store())], ctx=Store()), Name(id='c1', ctx=Store()), Starred(value=Name(id='b', ctx=Store()), ctx=Store())], ctx=Store())], ctx=Store())], value=Name(id='it', ctx=Load()))"),
    PyCodeCase('(a1): int = 1', SyntaxError, "AnnAssign(target=Name(id='a1', ctx=Store()), annotation=Name(id='int', ctx=Load()), value=Num(n=1), simple=0)"),
    PyCodeCase('a2: int = 2', SyntaxError, "AnnAssign(target=Name(id='a2', ctx=Store()), annotation=Name(id='int', ctx=Load()), value=Num(n=2), simple=1)"),
    PyCodeCase('c: int', SyntaxError, "AnnAssign(target=Name(id='c', ctx=Store()), annotation=Name(id='int', ctx=Load()), value=None, simple=1)"),
    PyCodeCase('c.v: int', SyntaxError, "AnnAssign(target=Attribute(value=Name(id='c', ctx=Load()), attr='v', ctx=Store()), annotation=Name(id='int', ctx=Load()), value=None, simple=0)"),
    PyCodeCase('del variable', None, "Delete(targets=[Name(id='variable', ctx=Del())])", assert_get_names=(set(), {'variable'}, set())),
    PyCodeCase('k += 11', None, "AugAssign(target=Name(id='k', ctx=Store()), op=Add(), value=Num(n=11))", assert_get_names=(set(), {'k'}, set())),
    PyCodeCase('k |= 11', None, "AugAssign(target=Name(id='k', ctx=Store()), op=BitOr(), value=Num(n=11))", assert_get_names=(set(), {'k'}, set())),
    PyCodeCase('pass', None, "Pass()", assert_get_names=(set(), set(), set())),
    PyCodeCase('assert k', None, "Assert(test=Name(id='k', ctx=Load()), msg=None)", assert_get_names=(set(), {'k'}, set())),
    PyCodeCase('import xxx', None, "Import(names=[alias(name='xxx', asname=None)])", assert_get_names=({'xxx'}, set(), set())),
    PyCodeCase('from x import y', None, "ImportFrom(module='x', names=[alias(name='y', asname=None)], level=0)", assert_get_names=({'y'}, set(), set())),
    PyCodeCase('from x import *', None, "ImportFrom(module='x', names=[alias(name='*', asname=None)], level=0)", assert_get_names=(set(), set(), set())),
    PyCodeCase('from x import y as z', None, "ImportFrom(module='x', names=[alias(name='y', asname='z')], level=0)", assert_get_names=({'z'}, set(), set())),
    PyCodeCase('from ..foo.bar import a as b, c', None, "ImportFrom(module='foo.bar', names=[alias(name='a', asname='b'), alias(name='c', asname=None)], level=2)", assert_get_names=({'b', 'c'}, set(), set())),
    PyCodeCase('raise x from y', None, "Raise(exc=Name(id='x', ctx=Load()), cause=Name(id='y', ctx=Load()))", assert_get_names=(set(), {'x', 'y'}, set())),
    PyCodeCase('break', None, "Break()", assert_get_names=(set(), set(), set())),
    PyCodeCase('continue', None, "Continue()", assert_get_names=(set(), set(), set())),
    PyCodeCase('return', None, "Return(value=None)", assert_get_names=(set(), set(), set())),
    PyCodeCase('global x', None, "Global(names=['x'])"),
    PyCodeCase('nonlocal x', None, "Nonlocal(names=['x'])"),
    PyCodeCase('if 1: print(2)', None, "If(test=Num(n=1), body=[Expr(value=Call(func=Name(id='print', ctx=Load()), args=[Num(n=2)], keywords=[]))], orelse=[])", assert_get_names=(set(), {'print'}, set())),
    PyCodeCase('if 1: z = k', None, "If(test=Num(n=1), body=[Assign(targets=[Name(id='z', ctx=Store())], value=Name(id='k', ctx=Load()))], orelse=[])", assert_get_names=({'z'}, {'k'}, set())),
    PyCodeCase('for a in b: print(1)', None, "For(target=Name(id='a', ctx=Store()), iter=Name(id='b', ctx=Load()), body=[Expr(value=Call(func=Name(id='print', ctx=Load()), args=[Num(n=1)], keywords=[]))], orelse=[])", assert_get_names=({'a'}, {'b', 'print'}, set())),
    PyCodeCase('for a in b: z = k', None, "For(target=Name(id='a', ctx=Store()), iter=Name(id='b', ctx=Load()), body=[Assign(targets=[Name(id='z', ctx=Store())], value=Name(id='k', ctx=Load()))], orelse=[])", assert_get_names=({'z', 'a'}, {'b', 'k'}, set())),
    PyCodeCase('for a in b: z = a', None, "For(target=Name(id='a', ctx=Store()), iter=Name(id='b', ctx=Load()), body=[Assign(targets=[Name(id='z', ctx=Store())], value=Name(id='a', ctx=Load()))], orelse=[])", assert_get_names=({'z', 'a'}, {'b', 'a'}, set())),
    PyCodeCase('while False: print(z)', None, "While(test=NameConstant(value=False), body=[Expr(value=Call(func=Name(id='print', ctx=Load()), args=[Name(id='z', ctx=Load())], keywords=[]))], orelse=[])", assert_get_names=(set(), {'print', 'z'}, set())),
    PyCodeCase('with connection(): print(2)', None, "With(items=[withitem(context_expr=Call(func=Name(id='connection', ctx=Load()), args=[], keywords=[]), optional_vars=None)], body=[Expr(value=Call(func=Name(id='print', ctx=Load()), args=[Num(n=2)], keywords=[]))])", assert_get_names=(set(), {'connection', 'print'}, set())),
    PyCodeCase('with a as b, open() as f: f.write(2)', None, "With(items=[withitem(context_expr=Name(id='a', ctx=Load()), optional_vars=Name(id='b', ctx=Store())), withitem(context_expr=Call(func=Name(id='open', ctx=Load()), args=[], keywords=[]), optional_vars=Name(id='f', ctx=Store()))], body=[Expr(value=Call(func=Attribute(value=Name(id='f', ctx=Load()), attr='write', ctx=Load()), args=[Num(n=2)], keywords=[]))])", assert_get_names=({'b', 'f'}, {'open', 'a', 'f'}, set())),
    PyCodeCase('def func1(b=1, c=2, *d, e, f=3, **g): return b + c + d', None, "FunctionDef(name='func1', args=arguments(args=[arg(arg='b', annotation=None), arg(arg='c', annotation=None)], vararg=arg(arg='d', annotation=None), kwonlyargs=[arg(arg='e', annotation=None), arg(arg='f', annotation=None)], kw_defaults=[None, Num(n=3)], kwarg=arg(arg='g', annotation=None), defaults=[Num(n=1), Num(n=2)]), body=[Return(value=BinOp(left=BinOp(left=Name(id='b', ctx=Load()), op=Add(), right=Name(id='c', ctx=Load())), op=Add(), right=Name(id='d', ctx=Load())))], decorator_list=[], returns=None)"),
    PyCodeCase('class Cl1(CL2): a = 2; b = 2', None, "ClassDef(name='Cl1', bases=[Name(id='CL2', ctx=Load())], keywords=[], body=[Assign(targets=[Name(id='a', ctx=Store())], value=Num(n=2)), Assign(targets=[Name(id='b', ctx=Store())], value=Num(n=2))], decorator_list=[])"),
    PyCodeCase('@dec1 def fff(): pass', SyntaxError, ""),
    PyCodeCase('try: func(2)', SyntaxError, ""),
    PyCodeCase('try: f.write(2); finally: f.close()', SyntaxError, ""),
    PyCodeCase('async def func1(b=1, c=2, *d, e, f=3, **g): return await e()', None, "AsyncFunctionDef(name='func1', args=arguments(args=[arg(arg='b', annotation=None), arg(arg='c', annotation=None)], vararg=arg(arg='d', annotation=None), kwonlyargs=[arg(arg='e', annotation=None), arg(arg='f', annotation=None)], kw_defaults=[None, Num(n=3)], kwarg=arg(arg='g', annotation=None), defaults=[Num(n=1), Num(n=2)]), body=[Return(value=Await(value=Call(func=Name(id='e', ctx=Load()), args=[], keywords=[])))], decorator_list=[], returns=None)"),
    PyCodeCase('async with a as b, open() as f: f.write(2)', SyntaxError, ""),
    PyCodeCase('async for a in b: print(1)', SyntaxError, ""),
    PyCodeCase('async while False: print(z)', SyntaxError, ""),
]


def _dump(tokens):
    # cros py3.5 py3.6
    return ast.dump(tokens).replace(", is_async=0", "")

# @pytest.mark.skip
@pytest.mark.parametrize("case", PY3LINE_TESTS)
def test_py3line_cases(case):
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write('\n'.join(case.input).encode('utf-8')); f.flush();
        command = 'cat {0} | {1} {2}'.format(f.name, PY3LINE, shlex.quote('; '.join(case.actions)))
        print(command)
        code, text = subprocess.getstatusoutput(command)
        output = text.split('\n')
        if case.full_check:
            assert output == case.output
        else:
            for line in case.output:
                assert line in output
        assert code == case.code

# @pytest.mark.skip
@pytest.mark.parametrize("case", PYCODE_TESTS)
def test_pycode_cases(case):
    try:
        tokens = to_tokens(case.code)
        assert _dump(tokens) == case.tokens
    except Exception as exc:
        if type(exc) == case.exception:
            pass
        else:
            raise
    if case.assert_get_names is not None:
        names = get_names(tokens)
        assert names == case.assert_get_names
