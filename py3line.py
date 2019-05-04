#!/usr/bin/env python3

# updated 2005.07.21, thanks to Jacob Oscarson
# updated 2006.03.30, thanks to Mark Eichin
# updated 2016.07.19, thanks to Pahaz White
# updated 2019.05.01, thanks to Pahaz White (v0.2.0)

from io import BytesIO
import tokenize
from pprint import pprint
from collections import namedtuple
import logging
import argparse
import tempfile
import traceback
from collections.abc import Iterable
import sys

__version__ = '0.2.0'
NAME = 'py3line'
logger = logging.getLogger(NAME)

if sys.version_info[0] != 3:
    raise RuntimeError("Only python 3.x is supported")

IN_STREAM = r'line.rstrip("\r\n") for line in sys.stdin if line'
CODE_HEAD = '''
import os
import sys
import types
import re
import shlex
import shutil
import pathlib
import operator
import collections
import itertools
import functools
import json
import base64
import random
import time
import subprocess

skip = object()

def flatten(list_of_lists):
    return itertools.chain.from_iterable(list_of_lists)

def most_common(stream):
    return collections.Counter(stream).most_common()

def print_stream(stream):
    for x in stream:
        if x is skip:
            continue
        elif isinstance(x, Iterable) and not isinstance(x, (str, bytes, bytearray)):
            print(*x, file=sys.stdout)
        else:
            print(x, file=sys.stdout)
'''


def to_tokens(expr):
    return list(tokenize.tokenize(BytesIO(expr.encode('utf-8')).readline))[1:-1]


def get_set_variable_name(tokens):
    set_var_operators = {'='}
    is_set_variable = (
        len(tokens) > 2 and tokens[0].type == tokenize.NAME
        and tokens[1].type == tokenize.OP
        and tokens[1].string in set_var_operators)
    return None if not is_set_variable else tokens[0].string


def _preprocess_expressions(exprs):
    Action = namedtuple('Action', 'expr, tokens, code, warns, is_element_based_action, is_stream_based_action, is_pre_action, is_statement_action, stream_based_actions_group')
    actions = []
    variables = set()
    stream_based_actions_group = 0
    has_stream = False
    prev_is_stream_based_action = False
    stream_based_markers = {'stream'}
    element_based_markers = {'x'}
    stream_markers = element_based_markers | stream_based_markers
    for expr in exprs:
        tokens = to_tokens(expr)
        warns = []

        # stream block
        is_element_based_action = any(
            (token.type == tokenize.NAME and 
             any(marker == token.string for marker in element_based_markers))
            for token in tokens)
        is_stream_based_action = any(
            (token.type == tokenize.NAME and 
             any(marker == token.string for marker in stream_based_markers))
            for token in tokens)
        if is_element_based_action and is_stream_based_action:
            # ex: (k for x in stream for k in x)
            is_element_based_action = False
            is_stream_based_action = True
        is_stream = is_element_based_action or is_stream_based_action

        if is_stream and not has_stream:
            has_stream = True
            stream_based_actions_group = 1
        elif is_stream_based_action:
            stream_based_actions_group += 1
        elif prev_is_stream_based_action:
            stream_based_actions_group += 1

        # set variable statment block
        # TODO(pahaz): add support `x1, x2 = 1, 2` and unpacking!
        # TODO(pahaz): add support `x12 += 1`
        set_variable_name = get_set_variable_name(tokens)
        if set_variable_name:
            if set_variable_name in stream_markers:
                # VAR = EXPR -transform-to-> EXPR
                err_expr = expr
                expr = expr.split('=', 1)[1].strip()
                tokens = tokens[2:]
                warns.append(f"use `{expr}` instead of `{err_expr}`")
            else:
                variables.add(set_variable_name)

        # import checks
        if expr.startswith('import '):
            module_name = expr[len('import '):]
            warns.append(f'use `-m {module_name}` option instead of `{expr}`')

        is_pre_action = not is_stream and not has_stream
        is_statement_action = not is_stream and has_stream

        mode = 'eval' if is_stream else 'exec'
        try:
            compile(expr, NAME, mode)
        except Exception as exc:
            if mode == 'eval' and _is_compile_by_exec(expr):
                # TODO(pahaz): example `s = sum(stream)`
                if is_stream_based_action:
                    is_element_based_action = False
                    is_stream_based_action = True
                    is_pre_action = False
                    is_statement_action = False
                else:
                    is_element_based_action = False
                    is_stream_based_action = False
                    is_pre_action = not has_stream
                    is_statement_action = has_stream
            else:
                logger.error("ERROR: EXPR[%r]: %s", expr, exc)
                raise RuntimeError('compile expr problem')

        # print(tokens)
        # print(is_element_based_action, is_stream_based_action, is_pre_action, is_statement_action, stream_based_actions_group)
        actions.append(Action(expr, None, None, warns, is_element_based_action, is_stream_based_action, is_pre_action, is_statement_action, stream_based_actions_group))

        prev_is_stream_based_action = is_stream_based_action

    return actions, variables


def _is_compile_by_exec(expr):
    try:
        compile(expr, NAME, 'exec')
    except Exception:
        return False    
    return True


def _codegen(actions, variables, modules):
    variables = sorted(variables)
    modules = sorted(modules)
    lines = []

    for module in modules:
        lines.append(f'import {module}')

    lines.append(CODE_HEAD)

    call_stack = []
    prev_stream_based_actions_group = 0
    prev_is_in_loop = False

    for action in (x for x in actions if not x.is_pre_action):
        if prev_stream_based_actions_group < action.stream_based_actions_group:
            if prev_is_in_loop:
                lines.append(f'        yield x\n')
            lines.append(f'def stream_based_actions_{action.stream_based_actions_group}(stream):')
            call_stack.append(f'stream_based_actions_{action.stream_based_actions_group}')
            if variables:
                lines.append(f'    global {", ".join(variables)}')
            if action.is_element_based_action or action.is_statement_action:
                lines.append('    for x in stream:')

        if action.is_element_based_action:
            lines.append(f'        x = {action.expr}')
            lines.append(f'        if x is skip:')
            lines.append(f'            continue')
            prev_is_in_loop = True
        elif action.is_statement_action:
            lines.append(f'        {action.expr}')
            prev_is_in_loop = True
        elif action.is_stream_based_action:
            lines.append(f'    stream = {action.expr}')
            lines.append(f'    if isinstance(stream, (str, bytes, bytearray)):')
            lines.append(f'        yield stream')
            lines.append(f'    else:')
            lines.append(f'        try:')
            lines.append(f'            yield from stream')
            lines.append(f'        except Exception as exc:')
            lines.append(f'            if "is not iterable" in str(exc):')
            lines.append(f'                yield stream')
            lines.append(f'            else:')
            lines.append(f'                raise\n')
            prev_is_in_loop = False
        else:
            raise RuntimeError('unexpected!')

        prev_stream_based_actions_group = action.stream_based_actions_group

    if prev_is_in_loop:
        lines.append(f'        yield x\n')
    call_stack.append('print_stream')

    lines.append(f'if __name__ == "__main__":')
    for action in (x for x in actions if x.is_pre_action):
        lines.append(f'    {action.expr}')

    if call_stack:
        funcs = ''.join(reversed([f'{x}(' for x in call_stack])) + IN_STREAM + (')' * len(call_stack))
        lines.append(f'    {funcs}')

    return '\n'.join(lines)




def parseargs():
    description = (
        "Py3line is a UNIX command-line tool for a simple text stream "
        "processing by the Python one-liner scripts. Like grep, sed and awk."
    )

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('expressions',
                        metavar='expression', nargs='*',
                        help='<python_expression>')

    parser.add_argument('-m', '--modules',
                        dest='modules',
                        action='append',
                        default=[],
                        help='for m in modules: import m  #default: []')

    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true')
    parser.add_argument('-q', '--quiet',
                        dest='quiet',
                        action='store_true')

    parser.add_argument('--version',
                        dest='version',
                        action='store_true',
                        help='Print the version string')

    parser.add_argument('--code',
                        dest='code',
                        action='store_true')

    return parser.parse_args()



def _setup_logger(args):
    if not logger.handlers:  # if no handlers, add a new one (console)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s | %(levelname)-8s| %(message)s')
        )
        logger.addHandler(console_handler)

    if args.quiet:
        logger.setLevel(logging.CRITICAL)
    else:
        if args.verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.WARN)

    # capture_warnings
    logging.captureWarnings(True)
    pywarnings = logging.getLogger('py.warnings')
    pywarnings.handlers.extend(logger.handlers)


def try_to_write_to_tmp_py_file(data):
    try:
        with tempfile.NamedTemporaryFile(suffix='.py',prefix='go',delete=False) as fp:
            fp.write(data.encode('utf-8'))
        return fp.name
    except Exception:
        return None


def main():
    args = parseargs()
    _setup_logger(args)
    logger.debug('arguments: %r', args)

    expressions = [
        z.strip() for x in args.expressions
        for z in x.split(';') if z.strip()]
    modules = [
        z.strip() for x in args.modules
        for z in x.split(',') if z.strip()]

    actions, variables = _preprocess_expressions(expressions)
    code = _codegen(actions, variables, modules)

    if args.code:
        print(code)
    else:
        exit_code = 0
        try:
            name = try_to_write_to_tmp_py_file(code) or "<string>"
            try:
                exec(compile(code, name, 'exec'), globals())
            except Exception:
                etype, exc, tb = sys.exc_info()
                tb_offset = 1
                try:
                    import IPython.core.ultratb
                    itb = IPython.core.ultratb.VerboseTB(include_vars=False)
                    trace_text = itb.text(etype, exc, tb, tb_offset=tb_offset)
                except:
                    trace = ['Traceback (most recent call last):\n']
                    trace += traceback.extract_tb(tb).format()[tb_offset:]
                    trace += traceback.format_exception_only(etype,exc)
                    trace_text = ''.join(trace)
                    trace_text = trace_text.replace(name, "<string>")
                logger.error(trace_text)
                exit_code = 1
        finally:
            if os.path.exists(name):
                os.unlink(name)
        return (exit_code)


def show_tokens(s):
    pprint(to_tokens(s))

# show_tokens('')
# show_tokens('2')
# show_tokens('q = 7')
# show_tokens('q, w = 7, 8')
# show_tokens('x == 7')
# show_tokens('f()')
# show_tokens('if 1: continue')
# show_tokens('k += 11')
# show_tokens('(k for x in stream for k in x)')

# exec(_codegen(*_preprocess_expressions(['q = 7', 'w = 8', 'skip if x == q else x', 'x + w', 'sum(stream)', 'sum(stream)', 'x + w', 'w1, w2 = 7, 8', 'zz = 2'])))


if __name__ == '__main__':
    sys.exit(main())
