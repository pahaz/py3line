#!/usr/bin/env python3

# updated 2005.07.21, thanks to Jacob Oscarson
# updated 2006.03.30, thanks to Mark Eichin
# updated 2016.07.19, thanks to Pahaz White (v0.1.0)
# updated 2019.05.01, thanks to Pahaz White (v0.2.0)
# updated 2019.05.05, thanks to Pahaz White (v0.3.0)

import ast
from pprint import pprint
from collections import namedtuple, deque
from enum import Enum
import sys, os
import logging
import argparse
import tempfile
import traceback

__version__ = '0.3.1'
NAME = 'py3line'
LOGGER = logging.getLogger(NAME)
DEFAULT_MODULES = {
    'os', 'sys', 'types', 're', 'shlex', 'shutil', 'pathlib', 
    'operator', 'collections', 'itertools', 'functools', 
    'json', 'base64', 'random', 'time', 'subprocess'}
ActionTypes = Enum('ActionTypes', 'stream, element')
Action = namedtuple('Action', 'string, warns, type, group')
class Py3LineSyntaxError(SyntaxError): pass

if sys.version_info[0] != 3:
    raise RuntimeError("Only python 3.x is supported")

class _MyNodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.NameTypes = Enum('NameTypes', 'module, function')
        self.NameContext = namedtuple('NameContext', 'type, use_names, def_names, local_names')
        self._name_contexts = [self.NameContext(self.NameTypes.module, set(), set(), set())]
        self._current_names = self._name_contexts[-1].use_names
    def visit_Name(self, node):
        self._current_names.add(node.id)
    def visit_FunctionDef(self, node):
        raise Py3LineSyntaxError('`def` is not allowed to use')
    def visit_AsyncFunctionDef(self, node):
        raise Py3LineSyntaxError('`async def` is not allowed to use')
    def visit_ClassDef(self, node):
        raise Py3LineSyntaxError('`class` is not allowed to use')
    def visit_arguments(self, node):
        print(ast.dump(node))
        self.generic_visit(node)
    def visit_arg(self, node):
        current_local_names = self._name_contexts[-1].local_names
        current_local_names.add(node.arg)
        self.generic_visit(node)
    def visit_alias(self, node):
        current_def_names = self._name_contexts[-1].def_names
        name = node.asname if node.asname else node.name
        if name != '*':
            current_def_names.add(name)
        self.generic_visit(node)
    def visit_Global(self, node):
        raise Py3LineSyntaxError('`global` is not allowed to use')
    def visit_Nonlocal(self, node):
        raise Py3LineSyntaxError('`nonlocal` is not allowed to use')
    def visit_comprehension(self, node):
        self._current_names = self._name_contexts[-1].local_names
        self.visit(node.target)
        self._current_names = self._name_contexts[-1].use_names
        self.visit(node.iter)
        for if_ in node.ifs:
            self.visit(if_)
    def visit_Assign(self, node):
        self._current_names = self._name_contexts[-1].def_names
        for target in node.targets:
            self.visit(target)
        self._current_names = self._name_contexts[-1].use_names
        if node.value:
            self.visit(node.value)
    def visit_AnnAssign(self, node):
        raise Py3LineSyntaxError('variable assignment with type annatations is not allowed to use')
    def visit_For(self, node):
        self._current_names = self._name_contexts[-1].def_names
        self.visit(node.target)
        self._current_names = self._name_contexts[-1].use_names
        self.visit(node.iter)
        for target in node.body:
            self.visit(target)
    def visit_withitem(self, node):
        self._current_names = self._name_contexts[-1].def_names
        if node.optional_vars:
            self.visit(node.optional_vars)
        self._current_names = self._name_contexts[-1].use_names
        self.visit(node.context_expr)
    def visit_Try(self, node):
        raise Py3LineSyntaxError('`try` is not allowed to use')
    def visit_ExceptHandler(self, node):
        raise Py3LineSyntaxError('`except` is not allowed to use')
    def visit_AsyncWith(self, node):
        raise Py3LineSyntaxError('`async with` is not allowed to use')
    def visit_AsyncFor(self, node):
        raise Py3LineSyntaxError('`async for` is not allowed to use')
    def visit_Await(self, node):
        raise Py3LineSyntaxError('`await` is not allowed to use')

def to_tokens(expr):
    res = ast.parse(expr + '\n', mode='exec').body
    if len(res) != 1:
        raise Py3LineSyntaxError('unexpected multyline')
    return res[0]

def get_names(tokens):
    v = _MyNodeVisitor()
    v.visit(tokens)
    return v._name_contexts[-1].def_names, v._name_contexts[-1].use_names, v._name_contexts[-1].local_names

def parseargs():
    description = (
        "Py3line is a UNIX command-line tool for a simple text stream "
        "processing by the Python one-liner scripts. Like grep, sed and awk."
    )

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('expressions',
                        metavar='expression', nargs='*',
                        help='python comma separated expressions')

    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true')
    parser.add_argument('-q', '--quiet',
                        dest='quiet',
                        action='store_true')

    parser.add_argument('--version',
                        dest='version',
                        action='store_true',
                        help='print the version string')

    parser.add_argument('--pycode',
                        dest='pycode',
                        action='store_true',
                        help='show generated python code')

    return parser.parse_args()

def setup_logger(args):
    if not LOGGER.handlers:  # if no handlers, add a new one (console)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s | %(levelname)-8s| %(message)s')
        )
        LOGGER.addHandler(console_handler)

    if args.quiet:
        LOGGER.setLevel(logging.CRITICAL)
    else:
        if args.verbose:
            LOGGER.setLevel(logging.DEBUG)
        else:
            LOGGER.setLevel(logging.WARN)

    # capture_warnings
    logging.captureWarnings(True)
    pywarnings = logging.getLogger('py.warnings')
    pywarnings.handlers.extend(LOGGER.handlers)

def _preprocess_expressions(exprs):
    actions = []
    variables = set()
    used_variables = set()

    group = 1
    prev_type = ActionTypes.stream
    
    stream_markers = {'stream'}
    element_markers = {'line'}

    for expr in exprs:
        if not expr:
            continue

        tokens = to_tokens(expr)
        def_names, used_names, _ = get_names(tokens)
        variables |= def_names
        used_variables |= used_names
        warns = []

        has_stream_marker = (def_names | used_names) & stream_markers
        has_element_marker = (def_names | used_names) & element_markers
        if has_stream_marker:
            current_type = ActionTypes.stream
        elif has_element_marker:
            current_type = ActionTypes.element
        else:
            current_type = prev_type

        if current_type != prev_type and actions:
            group += 1

        LOGGER.debug('action: %r, warns=%r, type=%s, group=%r, def_names=%r', 
                     expr, warns, current_type, group, def_names)
        actions.append(Action(expr, warns, current_type, group))
        prev_type = current_type

    return actions, variables, used_variables

def _codegen(actions, variables: set, used_variables: set, modules: set) -> str:
    if not actions:
        return ''
    variables = ", ".join(sorted(variables - {'stream', 'line'}))
    modules = sorted(modules | DEFAULT_MODULES & used_variables | {'sys'})
    lines = []

    for module in modules:
        lines.append('import {module}'.format(module=module))
    lines.append('')

    prev_type = ActionTypes.stream
    prev_group = 0
    transforations = deque()

    for action in actions:
        if prev_group < action.group:
            if prev_group:
                if prev_type == ActionTypes.element:
                    lines.append('        yield line\n')
                elif prev_type == ActionTypes.stream:
                    lines.append('    return stream\n')
                else:
                    raise RuntimeError('unexpected!')
            func_prefix = 'transform' if action.type == ActionTypes.stream else 'process'
            func_name = '{func_prefix}{action.group}'.format(action=action, func_prefix=func_prefix)
            lines.append('def {func_name}(stream):'.format(func_name=func_name))
            transforations.appendleft(func_name)
            if variables:
                lines.append('    global {variables}'.format(variables=variables))
            if action.type == ActionTypes.element:
                lines.append('    for line in stream:')

        if action.type == ActionTypes.element:
            lines.append('        {action.string}'.format(action=action))
        elif action.type == ActionTypes.stream:
            lines.append('    {action.string}'.format(action=action))
        else:
            raise RuntimeError('unexpected!')

        prev_type = action.type
        prev_group = action.group

    if prev_type == ActionTypes.element:
        lines.append('        yield line\n')
    elif prev_type == ActionTypes.stream:
        lines.append('    return stream\n')
    else:
        raise RuntimeError('unexpected!')

    lines.append('if __name__ == "__main__":')
    if transforations:
        lines.append('    stream = (line.rstrip("\\r\\n") for line in sys.stdin if line)')
        funcs = '('.join(transforations) + '(stream' + ')' * len(transforations)
        lines.append('    stream = {funcs}'.format(funcs=funcs))
        lines.append('    for line in stream: pass')

    return '\n'.join(lines)

def _try_to_write_to_tmp_py_file(data):
    try:
        with tempfile.NamedTemporaryFile(prefix='py3_', delete=False) as fp:
            fp.write(data.encode('utf-8'))
        return fp.name
    except Exception as exc:
        LOGGER.debug('write to tmp.py error: %s', exc)
        return None

def execute(code):
    exit_code = 0
    try:
        name = _try_to_write_to_tmp_py_file(code) or "<string>"
        LOGGER.debug('write to tmp.py: %s', name)
        try:
            exec(compile(code, name, 'exec'), globals())
        except Exception:
            etype, exc, tb = sys.exc_info()
            tb_offset = 1
            try:
                import IPython.core.ultratb
                itb = IPython.core.ultratb.VerboseTB(include_vars=False)
                trace_text = itb.text(etype, exc, tb, tb_offset=tb_offset)
            except Exception as exc2:
                LOGGER.debug('exec() error handler extension: %s', exc2)
                trace = ['Traceback (most recent call last):\n']
                trace += traceback.extract_tb(tb).format()[tb_offset:]
                trace += traceback.format_exception_only(etype, exc)
                trace_text = ''.join(trace)
                trace_text = trace_text.replace(name, "<string>")
            LOGGER.error(trace_text)
            exit_code = 1
    finally:
        if os.path.exists(name):
            LOGGER.debug('remove tmp.py: %s', name)
            os.unlink(name)
    return exit_code

def main():
    args = parseargs()
    setup_logger(args)
    LOGGER.debug('arguments: %r', args)

    expressions = [
        z.strip() for x in args.expressions
        for z in x.split(';') if z.strip()]
    modules = set()

    actions, variables, used_variables = _preprocess_expressions(expressions)
    code = _codegen(actions, variables, used_variables, modules)

    if args.pycode:
        print(code)
    elif args.version:
        print(__version__)
    else:
        return execute(code)
    return 0


if __name__ == '__main__':
    sys.exit(main())
