**Author**: `Pahaz Blinov`_

**Repo**: https://github.com/pahaz/py3line/

Pyline is a UNIX command-line tool for line-based processing
in Python with regex and output transform features
similar to grep, sed, and awk.

This project inspired by: `piep`_, `pysed`_, `pyline`_, `pyp`_ and
`Jacob+Mark recipe <https://code.activestate.com/recipes/437932-pyline-a-grep-like-sed-like-command-line-tool/>`_

**requirements**: Python3

**WHY I MAKE IT?**

I sometimes have to use `sed` / `awk`.
Not often, and so I always forget the necessary options and `sed` / `awk` DSL.
But I now python, I like it, and I want use it for data processing.
Default `python -c` is hard to write the kind of one-liner that works well.

Why not a `pyline`?
 * Don`t support python3
 * Have many options (I want as much simple as possible solution)
 * Bad performance
 * Don`t support command chaining

Why not a `pysed`?
 *

Installation
============

`py3line`_ is on PyPI, so simply run:

::

    pip install py3line

or ::

    easy_install py3line

to have it installed in your environment.

For installing from source, clone the
`repo <https://github.com/pahaz/py3line>`_ and run::

    python setup.py install

Tutorial
========

Lets start with two simple examples:

.. code-block:: bash

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "x.split()" -a "len(x)"
    2
    1
    3

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "x.split()" -a "len(x)" -a "sum(xx)"
    6

How it works?
-------------

Py3line produces a transform over the input data stream.
Py3line transform is constructed from a sequence of python actions.
Each action can be an action **over an element of stream** or
an action **over the stream**.

First example overview ::

    echo -e "Here are\nsome\nwords for you." | ./py3line.py "x.split()" -a "len(x)"

 * **echo -e "Here are\nsome\nwords for you."** -- create an input stream data consists of three lines
 * **|** -- pipeline input stream to py3line
 * **"x.split()" -a "len(x)"** -- define two actions: "x.split()" and "len(x)". Each of them is element based action

Py3line expects to get at least one transformation action as positional argument.
You also can define additional action by using **-a** arguments,
as shown in the example above.

The example above can be represented as the following python pseudo-code::

    import sys

    for x in sys.stdin.readlines():

        # 1) action "x.split()"
        x = x.split()

        # 2) action "len(x)"
        x = len(x)

        print(x)

Second example overview ::

    echo -e "Here are\nsome\nwords for you." | ./py3line.py "x.split()" -a "len(x)" -a "sum(xx)"

Here we have stream based action **"sum(xx)"**.

It can be represented as python pseudo-code::

    import sys

    xx = [x for x in sys.stdin.readlines()]

    for x in xx:

        # 1) action "x.split()"
        x = x.split()

        # 2) action "len(x)"
        x = len(x)

    # 3) action "sum(xx)"
    print(sum(xx))

What is order actions?
----------------------

This commands are equal::

    ./py3line.py "x.split()" -a "len(x)" -a "sum(xx)"
    ./py3line.py -a "x.split()" "len(x)" -a "sum(xx)"
    ./py3line.py -a "x.split()" -a "len(x)" "sum(xx)"

But we recommend use::

    ./py3line.py "x.split()" -a "len(x)" -a "sum(xx)"

as the right actions ordering.

Why it so? Because you must pass one action as positional argument.

Actions chaining
----------------

Let us define some terminology. **py3line action1 -a action2 -a action3**

We have actions: action1, action2 and action3.
Each of them may be element based or stream based.

**Element based** action can be represented as python pseudo-code::

    xx = ...
    new_xx = []

    for x in xx:
        # DO ELEMENT BASED ACTION ON `x`
        result = eval(compile(action_x, ..., 'eval'), {'x': x})
        new_xx.append(result)

    xx = new_xx

**Stream based** action can be represented as python pseudo-code::

    xx = ...

    # DO STREAM BASED ACTION ON `xx`
    xx = eval(compile(action_xx, ..., 'eval'), {'xx': xx})

Pre-actions
-----------

Sometimes you want prepare some variables or import some modules.

You can use **-m** options for import module::

    ./py3line.py -m shlex "shlex.split(x)[13]"

You also can use **-p** options for run exec some actions before processing::

    ./py3line.py -p "rgx = re.compile(r' is ([A-Z]\w*)')" "rgx.search(x).group(1)"

Pseudo code example **./py3line.py -m module1 -m module2 -p pre-action1  -p pre-action2 ...** ::

    import module1
    import module2

    pre-action1
    pre-action2

    ...

**Options ordering**

Regardless of the sequence definition. First be made all imports (**-m** option),
then be made all pre-action (**-p** option), and
then actions (**-a** option + 1st positional argument).

.. code-block:: bash

    # Print every line (null transform)
    $ cat ./testsuit/test.txt | ./py3line.py x
    This is my cat,
     whose name is Betty.
    This is my dog,
     whose name is Frank.
    This is my fish,
     whose name is George.
    This is my goat,
     whose name is Adam.

    # Number every line
    $ cat ./testsuit/test.txt | ./py3line.py "i, x"
    0 This is my cat,
    1  whose name is Betty.
    2 This is my dog,
    3  whose name is Frank.
    4 This is my fish,
    5  whose name is George.
    6 This is my goat,
    7  whose name is Adam.

    # Print every first and last word
    $ cat ./testsuit/test.txt | ./py3line.py "x.split()[0], x.split()[-1]"
    This cat,
    whose Betty.
    This dog,
    whose Frank.
    This fish,
    whose George.
    This goat,
    whose Adam.

    # Split into words and print (strip al non word char like comma, dot, etc)
    $ cat ./testsuit/test.txt | ./py3line.py "re.findall(r'\w+', x)"
    This is my cat
    whose name is Betty
    This is my dog
    whose name is Frank
    This is my fish
    whose name is George
    This is my goat
    whose name is Adam

    # Regex matching with groups
    $ cat ./testsuit/test.txt | ./py3line.py "re.findall(r' is ([A-Z]\w*)', x) or False"
    Betty
    Frank
    George
    Adam

    # cat ./testsuit/test.txt | ./py3line.py "re.search(r' is ([A-Z]\w*)', x).group(1)"
    $ cat ./testsuit/test.txt | ./py3line.py -p "rgx = re.compile(r' is ([A-Z]\w*)')" "rgx.search(x).group(1)"
    Betty
    Frank
    George
    Adam

    ## Original Examples
    # Print out the first 20 characters of every line
    # cat ./testsuit/test.txt | ./py3line.py "i < 2"
    $ cat ./testsuit/test.txt | ./py3line.py "list(xx)[:2]"
    This is my cat,
     whose name is Betty.

    # Print just the URLs in the access log
    $ cat ./testsuit/nginx.log | ./py3line.py -m shlex "shlex.split(x)[13]"
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    GET /admin/moktoring/session/add/ HTTP/1.1
    GET /admin/jsi18n/ HTTP/1.1
    GET /static/admin/img/icon-calendar.svg HTTP/1.1
    GET /static/admin/img/icon-clock.svg HTTP/1.1
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    HEAD / HTTP/1.0
    GET /logout/?reason=startApplication HTTP/1.1
    GET / HTTP/1.1
    GET /login/?next=/ HTTP/1.1
    POST /admin/customauth/user/?q=%D0%9F%D0%B0%D1%81%D0%B5%D1%87%D0%BD%D0%B8%D0%BA HTTP/1.1

    # Print most common accessed urls and filter accessed more then 5 times
    $ cat ./testsuit/nginx.log | ./py3line.py -m shlex -m collections  -a "shlex.split(x)[13]" -a "collections.Counter(xx).most_common()" "x[1] > 5 and x[0]"
    HEAD / HTTP/1.0


HELP
----

::

    usage: py3line.py [-h] [-a action] [-p pre_action] [-o OUTPUT] [-i]
                      [--in-place-suffix IS_INPLACE_SUFFIX] [-m MODULES] [-v] [-q]
                      [--version]
                      action [file [file ...]]

    Py3line is a UNIX command-line tool for line-based processing in Python with
    regex and output transform features similar to grep, sed, and awk.

    positional arguments:
      action                <python_expression>
      file                  Input file #default: stdin

    optional arguments:
      -h, --help            show this help message and exit
      -a action, --action action
                            <python_expression>
      -p pre_action, --pre-action pre_action
                            <python_expression>
      -o OUTPUT, --out OUTPUT, --output-file OUTPUT
                            Output file #default: '-' for stdout
      -i, --in-place        Output to editable file
      --in-place-suffix IS_INPLACE_SUFFIX
                            Output to editable file and provide a backup suffix
                            for keeping a copy of the original file
      -m MODULES, --modules MODULES
                            for m in modules: import m #default: []
      -v, --verbose
      -q, --quiet
      --version             Print the version string


.. _Pahaz Blinov: https://github.com/pahaz/
.. _py3line: https://pypi.python.org/pypi/py3line/
.. _pyp: https://pypi.python.org/pypi/pyp/
.. _piep: https://github.com/timbertson/piep/tree/master/piep/
.. _pysed: https://github.com/dslackw/pysed/blob/master/pysed/main.py
.. _pyline: https://github.com/westurner/pyline/blob/master/pyline/pyline.py
