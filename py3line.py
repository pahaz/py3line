#!/usr/bin/env python3

# updated 2005.07.21, thanks to Jacob Oscarson
# updated 2006.03.30, thanks to Mark Eichin
# updated 2016.07.19, thanks to Pahaz White

import logging
import os
import shlex
import subprocess
import sys
import re
import argparse
import tokenize
import types
import pathlib
import time
import datetime
from io import BytesIO
from pprint import pprint

__version__ = '0.0.5'
NAME = 'py3line'
logger = logging.getLogger(NAME)
skip = object()

if sys.version_info[0] != 3:
    raise RuntimeError("Only python 3.x is supported")


def x_processor(reader, index, expr, compiled_expr, global_ctx):
    """
    Line based action processor
    """
    for i, x in enumerate(reader):
        if isinstance(x, str) and x.endswith('\n'):
            x = x[:-1]

        try:
            result = eval(compiled_expr, global_ctx, locals())
        except Exception as exc:
            logger.info("EXPR[%d]: %r, LINE[%d]: %r, ERROR: %r",
                        index, expr, i, x, exc)
            continue

        if result is skip:
            logger.debug("EXPR[%d]: %r, LINE[%d]: %r, SKIP",
                         index, expr, i, x)
            continue

        logger.debug("EXPR[%d]: %r, LINE[%d]: %r => %r",
                     index, expr, i, x, result)
        yield result


def xx_processor(reader, index, expr, compiled_expr, global_ctx):
    """
    Stream transformation action (Stream based processor)
    """
    xx = reader
    try:
        result = eval(compiled_expr, global_ctx, locals())
    except TypeError as _exc:
        # fix xx[:3], xx[1:-1], ...
        if str(_exc).find("object is not subscriptable") != -1:
            logger.debug("EXPR[%d]: %r MEMORIZE STREAM", index, expr)
            xx = list(xx)
            result = eval(compiled_expr, global_ctx, locals())
        else:
            raise _exc
    logger.debug("EXPR[%d]: %r => %r", index, expr, result)
    return result


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


def _split_expressions(exprs):
    """
    >>> _split_expressions(["x.split()"])
    ([], ['x.split()'], [], [])
    >>> _split_expressions(["xxx = re.compile('[a-z]')"])
    (["xxx = re.compile('[a-z]')"], [], [], [])
    >>> _split_expressions(["x.split()", "xxx = re.compile('[a-z]')"])
    (["xxx = re.compile('[a-z]')"], ['x.split()'], ["xxx = re.compile('[a-z]')"], [])
    >>> _split_expressions(["int(x) - 1", "sum(xx)"])
    ([], ['int(x) - 1', 'sum(xx)'], [], [])
    >>> _split_expressions(["int(x) - 1", "import xxx"])
    (['import xxx'], ['int(x) - 1'], ['import xxx'], ['import xxx'])
    >>> _split_expressions(["import xxx"])
    (['import xxx'], [], [], ['import xxx'])
    >>> _split_expressions(["int(x)", "sum(xx)", "x = 1"])
    ([], ['int(x)', 'sum(xx)', 'x = 1'], [], [])
    >>> _split_expressions(['y', 'y.w()', 'import xxx'])
    (['y', 'y.w()', 'import xxx'], [], [], ['import xxx'])
    """
    pre_actions = []
    stream_actions = []
    warn_pre_actions = []
    warn_imports = []

    stream_markers = ['i', 'x', 'xx']
    for expr in exprs:
        tokens = tokenize.tokenize(BytesIO(expr.encode('utf-8')).readline)
        is_stream = any(
            (token.type == tokenize.NAME and
             any(marker == token.string for marker in stream_markers))
            for token in tokens
        )
        if is_stream:
            stream_actions.append(expr)
        else:
            pre_actions.append(expr)

            if stream_actions:
                warn_pre_actions.append(expr)

        if expr.startswith('import '):
            warn_imports.append(expr)

    return pre_actions, stream_actions, warn_pre_actions, warn_imports


def _import_modules(modules, global_ctx):
    for i, module in enumerate(modules):
        try:
            global_ctx[module] = __import__(module, global_ctx, global_ctx)
        except Exception as exc:
            logger.error("IMPORT[%d]: %r, ERROR: %r", i, module, exc)
            raise


def _pre_actions(pre_exprs, global_ctx):
    for i, expr in enumerate(pre_exprs):
        try:
            compiled_expr = compile(expr, NAME, 'exec')
            exec(compiled_expr, global_ctx, global_ctx)
        except Exception as exc:
            logger.error("EXPR[%d]: %r, ERROR: %r", i, expr, exc)
            raise


def _get_actions(exprs):
    actions = []
    for i, expr in enumerate(exprs):
        try:
            tokens = tokenize.tokenize(BytesIO(expr.encode('utf-8')).readline)
            is_full_stream_processor = any(
                (token.type == tokenize.NAME and token.string == 'xx')
                for token in tokens)
            compiled_expr = compile(expr, NAME, 'eval')
            actions.append((i, expr, compiled_expr, is_full_stream_processor))
        except Exception as exc:
            logger.error("EXPR[%d]: %r, ERROR: %r", i, expr, exc)
            raise
    return actions


def _process_result(writer, result):
    is_stdin = result is sys.stdin
    if result is None or result is False or result is skip or is_stdin:
        return
    elif isinstance(result, list) or isinstance(result, tuple):
        result = ' '.join(map(str, result))
    else:
        result = str(result)
    if not result.endswith('\n'):
        result += '\n'

    writer.write(result)


def _process_results(writer, results):
    for result in results:
        if result is None or result is False or result is skip or \
                isinstance(result, Exception):
            continue
        elif isinstance(result, list) or isinstance(result, tuple):
            result = ' '.join(map(str, result))
        else:
            result = str(result)
        if not result.endswith('\n'):
            result += '\n'

        writer.write(result)
        # print(result, file=writer)


def global_run(*x, stdout=subprocess.PIPE, check=False, shell=True, **kwargs):
    return subprocess.run(
        *x, stdout=stdout, check=check, shell=shell,
        **kwargs)


def global_sh(*x, stdout=subprocess.PIPE, check=False, shell=True, **kwargs):
    result = global_run(*x, stdout=stdout, check=check, shell=shell, **kwargs)
    return result.stdout.decode() if result.returncode == 0 else skip


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
    pre_actions, stream_actions, warn_pre_actions, warn_imports = \
        _split_expressions(expressions)

    if warn_pre_actions:
        pre_no_imports = [x for x in pre_actions if x not in warn_imports]
        command = "; ".join(warn_imports + pre_no_imports + stream_actions)
        m_command = " -m " + repr(','.join(modules)) if modules else ''
        logger.warning("use command: %s%s %r", sys.argv[0], m_command, command)
    if args.version:
        print(__version__)
        return 0

    global_ctx = {
        'skip': skip,
        'os': os,
        'sys': sys,
        're': re,
        'shlex': shlex,
        'pprint': pprint,
        'run': global_run,
        'sh': global_sh,
        'STDOUT': subprocess.STDOUT,
        'PIPE': subprocess.PIPE,
        'DEVNULL': subprocess.DEVNULL,
    }

    try:
        _import_modules(modules, global_ctx)
        _pre_actions(pre_actions, global_ctx)
    except Exception:
        logger.error('exit(1)')
        return 1

    reader, writer = sys.stdin, sys.stdout
    actions = _get_actions(stream_actions)
    for i, expr, compiled_expr, is_full_stream_processor in actions:
        processor = xx_processor if is_full_stream_processor else x_processor
        reader = processor(reader, i, expr, compiled_expr, global_ctx)

    results = reader
    if isinstance(results, types.GeneratorType):
        _process_results(writer, results)
    else:
        _process_result(writer, results)

    return 0


if __name__ == '__main__':
    sys.exit(main())
