**Author**: `Pahaz White`_

**Repo**: https://github.com/pahaz/py3line/

Pyline is a UNIX command-line tool for bash one-liner scripts.
It's python line alternative to `grep`, `sed`, and `awk`.

This project inspired by: `pyfil`_, `piep`_, `pysed`_, `pyline`_, `pyp`_ and
`Jacob+Mark recipe <https://code.activestate.com/recipes/437932-pyline-a-grep-like-sed-like-command-line-tool/>`_

**WHY I MAKE IT?**

Sometimes, I have to use `sed` / `awk` / `grep`. Usually for simple text
processing. Find some pattern inside the text file using Python regexp,
or comment/uncomment some config line by bash one line command.

I always forget the necessary options and `sed` / `awk` DSL.
But I now python, I like it, and I want use it for this simple bash tasks.
Default `python -c` is not enough to write readable bash one-liners.

Why not a `pyline`?
 * Don`t support python3
 * Have many options
 * Don`t support command chaining

**PRINCIPLES**

 * AS MUCH SIMPLE TO UNDERSTAND BASH ONE LINER SCRIPT AS POSSIBLE
 * LESS SCRIPT ARGUMENTS
 * AS MUCH EASY TO INSTALL AS POSSIBLE (CONTAINER FRIENDLY ???)
 * SMALL CODEBASE (less 500 loc)
 * LAZY AND EFFECTIVE AS POSSIBLE

Installation
============

`py3line`_ is on PyPI, so simply run:

::

    pip install py3line

or ::

    sudo curl -L "https://61-63976011-gh.circle-artifacts.com/0/py3line-$(uname -s)-$(uname -m)" -o /usr/local/bin/py3line
    sudo chmod +x /usr/local/bin/py3line

to have it installed in your environment.

For installing from source, clone the
`repo <https://github.com/pahaz/py3line>`_ and run::

    python setup.py install

Tutorial
========

Lets start with examples, we want to evaluate a number of words in each line:

.. code-block:: bash

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "x = len(line.split(' ')); print(x, line)"
    2 Here are
    1 some
    3 words for you.


Py3line process input stream by python code line by line.

 * **echo -e "Here are\nsome\nwords for you."** -- create an input stream consists of three lines
 * **|** -- pipeline input stream to py3line
 * **"x = len(line.split()); print(x, line)"** -- define 2 actions: "x = len(line.split(' '))" evaluate number of words in each line, then "print(x, line)" print the result. Each action apply to the input stream step by step.

The example above can be represented as the following python code::

    import sys

    def process(stream):
        for line in stream:
            x = len(line.split(' '))  # action 1
            print(x, line)            # action 2
            yield line

    stream = (line.rstrip("\r\n") for line in sys.stdin if line)
    stream = process(stream)
    for line in stream: pass

You can also get the executed python code by ``--pycode`` argument.

.. code-block:: bash

    $ ./py3line.py "x = len(line.split(' ')); print(x, line)" --pycode  #skipbashtest
    ...

Stream transform
----------------

Lets try more complex example, we want to to evaluate the number of words in the whole file. 
This value is easy to calculate if you convert the input stream from a stream of lines 
to a number of words in line stream. Just override ``line`` variable ::

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "line = len(line.split()); print(sum(stream))"
    6

Here we have a stream transformation action **"print(sum(stream))"**.

The example above can be represented as the following python code::

    import sys

    def process(stram):
        for line in stream:
            line = len(line.split())  # action 1
            yield line

    def transform(stream):
        print(sum(stream))            # action 2
        return stream

    stream = (line.rstrip("\r\n") for line in sys.stdin if line)
    stream = transform(process(stream))
    for line in stream: pass

You can also get the executed python code by ``--pycode`` argument.

.. code-block:: bash

    $ ./py3line.py "line = len(line.split()); print(sum(stream))" --pycode  #skipbashtest
    ...

Lazy as possible
----------------

Py3line does calculations only when necessary by the use of python generators.
This means that the input stream does not fit into memory and you can easy process more data than your RAM allows.

But it also imposes limitations on the ability to work with the data flow. 
You cannot use multiple aggregation functions at the same time. For example, 
if we want to calculate the maximum number of words in a line and the total number of words in a whole file at the same time.::

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "line = len(line.split()); print(sum(stream)); print(max(stream))"  #skipbashtest
    6
    2019-05-05 14:55:09,353 | ERROR   | Traceback (most recent call last):
      File "<string>", line 15, in <module>
        stream = transform2(process1(stream))
      File "<string>", line 10, in transform2
        print(max(stream))
    ValueError: max() arg is an empty sequence

We can see the ``empty sequence`` error. It throws because our ``stream`` generator is already empty. 
And we can't find any max value on empty stream.

stream memorization
~~~~~~~~~~~~~~~~~~~

We can solve it by converting the ``stream`` generator to a list of values in memory using python ``list(stream)`` function. ::

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "line = len(line.split()); stream = list(stream); print(sum(stream), max(stream))"
    6 3

The example above can be represented as the following python code::

    import sys

    def process(stram):
        for line in stream:
            line = len(line.split())     # action 1
            yield line

    def transform(stream):
        stream = list(stream)            # action 2
        print(sum(stream), max(stream))  # action 3
        return stream

    stream = (line.rstrip("\r\n") for line in sys.stdin if line)
    stream = transform(process(stream))
    for line in stream: pass

evaluate on the fly
~~~~~~~~~~~~~~~~~~~

We can also solve it without putting the stream into memory. Just use the auxiliary variables where 
we will place the calculated result in the process of processing the stream. ::

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "s = 0; m = 0; num_of_words = len(line.split()); s += num_of_words; m = max(m, num_of_words); print(s, m)"
    2 2
    3 2
    6 3

The example above can be represented as the following python code::

    import sys

    def process(stram):
        s = 0                                 # action 1
        m = 0                                 # action 2
        for line in stream:
            num_of_words = len(line.split())  # action 3
            s += num_of_words                 # action 4
            m = max(m, num_of_words)          # action 5
            print(s, m)                       # action 6
            yield line

    stream = (line.rstrip("\r\n") for line in sys.stdin if line)
    stream = process(stream)
    for line in stream: pass

But we want only the last result. We don't want to see intermediate results.
To do this, you can add a loop over all elements of the stream before printing 
by ``for line in stream: pass``. Don't worry, this loop doesn't add unnecessary calculations 
as we use Python language generators. The loop will simply force the stream 
to be iterated before the print function called. ::

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "s = 0; m = 0; num_of_words = len(line.split()); s += num_of_words; m = max(m, num_of_words); for line in stream: pass; print(s, m)"
    6 3

The example above can be represented as the following python code::

    import sys

    def process(stram):
        global s, m
        s = 0                                 # action 1
        m = 0                                 # action 2
        for line in stream:
            num_of_words = len(line.split())  # action 3
            s += num_of_words                 # action 4
            m = max(m, num_of_words)          # action 5
            yield line

    def transform(stream):
        global s, m
        for line in stream: pass              # action 6
        print(s, m)                           # action 7
        return stream

    stream = (line.rstrip("\r\n") for line in sys.stdin if line)
    stream = transform(process(stream))
    for line in stream: pass

python generator laziness
~~~~~~~~~~~~~~~~~~~~~~~~~

Let's check python generator laziness. 
Just run ``for line in stream: print(1);`` 
twice in a row::

    $ echo -e "Here are\nsome\nwords for you." | ./py3line.py "for line in stream: print(1); for line in stream: print(1)"
    1
    1
    1

As we can see, it only one-time iteration over the python generator items. 
And all subsequent iterations will work with an empty generator, 
which is equivalent to a cycle through an empty list.

The example above can be represented as the following python code::

    import sys

    def transform(stream):
        for line in stream: pass              # action 1 (3 iterations)
        for line in stream: pass              # action 2 (0 iterations)
        return stream

    stream = (line.rstrip("\r\n") for line in sys.stdin if line)
    stream = transform(stream)
    for line in stream: pass                  # (0 iterations)

work with a part of stream
~~~~~~~~~~~~~~~~~~~~~~~~~~

TODO ....

Details
=======

Let us define some terminology. **py3line "action1; action2; action3**

We have actions: action1, action2 and action3.
Each action have type. It may be ``element processing`` or ``stream transformation``.

We can understand the type of action based on the variables used in it. 
We have two variables: ``line`` and ``stream``. 
They are markers that define the type of action.

Lets look at some types from examples abow::

    x = line.split()                 -- element processing
    print(x, line)                   -- element processing
    print(sum(stream))               -- stream transformation
    stream = list(stream)            -- stream transformation
    print(sum(stream), max(stream))  -- stream transformation
    s = 0                            -- unidentified
    m = 0                            -- unidentified
    num_of_words = len(line.split()) -- element processing
    s += num_of_words                -- unidentified
    m = max(m, num_of_words)         -- unidentified
    print(s, m)                      -- unidentified
    for line in stream: pass         -- stream transformation

**[rule1]** If an action has an undefined type, it inherits its type from the previous action.
**[rule2]** If there is no previous action, then the action is considered a stream transformation.

Examples::

    s = 0                            -- stream transformation (because of [rule2])
    num_of_words = len(line.split()) -- element processing (because of `line` marker)
    s += num_of_words                -- element processing (because of [rule1])
    print(s)                         -- element processing (because of [rule1])

And if we want to do ``print`` at the and, we should have some `stream` marker in actions before. 

::

    s = 0                            -- stream transformation (because of [rule2])
    num_of_words = len(line.split()) -- element processing (because of `line` marker)
    s += num_of_words                -- element processing (because of [rule1])
    stream                           -- stream transformation (because of `stream` marker)
    print(s)                         -- stream transformation (because of [rule1])

Unfortunately, it is not so clearly to people who are not familiar with the the implementation.
Therefore, it is better to use a more explicit to readers actions like ``for line in stream: pass``.

::

    s = 0                            -- stream transformation (because of [rule2])
    num_of_words = len(line.split()) -- element processing (because of `line` marker)
    s += num_of_words                -- element processing (because of [rule1])
    for line in stream: pass         -- stream transformation (because of `stream` marker)
    print(s)                         -- stream transformation (because of [rule1])


Some examples
=============

.. code-block:: bash

    # Print every line (null transform)
    $ cat ./testsuit/test.txt | ./py3line.py "print(line)"
    This is my cat,
     whose name is Betty.
    This is my dog,
     whose name is Frank.
    This is my fish,
     whose name is George.
    This is my goat,
     whose name is Adam.

.. code-block:: bash

    # Number every line
    $ cat ./testsuit/test.txt | ./py3line.py "stream = enumerate(stream); print(line)"
    (0, 'This is my cat,')
    (1, ' whose name is Betty.')
    (2, 'This is my dog,')
    (3, ' whose name is Frank.')
    (4, 'This is my fish,')
    (5, ' whose name is George.')
    (6, 'This is my goat,')
    (7, ' whose name is Adam.')

.. code-block:: bash

    # Number every line
    $ cat ./testsuit/test.txt | ./py3line.py "stream = enumerate(stream); print(line[0], line[1])"
    0 This is my cat,
    1  whose name is Betty.
    2 This is my dog,
    3  whose name is Frank.
    4 This is my fish,
    5  whose name is George.
    6 This is my goat,
    7  whose name is Adam.

Or just ``cat ./testsuit/test.txt | ./py3line.py "stream = enumerate(stream); print(*line)"``

.. code-block:: bash

    # Print every first and last word
    $ cat ./testsuit/test.txt | ./py3line.py "s = line.split(); print(s[0], s[-1])"
    This cat,
    whose Betty.
    This dog,
    whose Frank.
    This fish,
    whose George.
    This goat,
    whose Adam.

.. code-block:: bash

    # Split into words and print as list (strip al non word char like comma, dot, etc)
    $ cat ./testsuit/test.txt | ./py3line.py "print(re.findall(r'\w+', line))"
    ['This', 'is', 'my', 'cat']
    ['whose', 'name', 'is', 'Betty']
    ['This', 'is', 'my', 'dog']
    ['whose', 'name', 'is', 'Frank']
    ['This', 'is', 'my', 'fish']
    ['whose', 'name', 'is', 'George']
    ['This', 'is', 'my', 'goat']
    ['whose', 'name', 'is', 'Adam']

.. code-block:: bash

    # Split into words (strip al non word char like comma, dot, etc)
    $ cat ./testsuit/test.txt | ./py3line.py "print(*re.findall(r'\w+', line))"
    This is my cat
    whose name is Betty
    This is my dog
    whose name is Frank
    This is my fish
    whose name is George
    This is my goat
    whose name is Adam

.. code-block:: bash

    # Find all three letter words
    $ cat ./testsuit/test.txt | ./py3line.py "print(re.findall(r'\b\w\w\w\b', line))"
    ['cat']
    []
    ['dog']
    []
    []
    []
    []
    []

.. code-block:: bash

    # Find all three letter words + skip empty lists
    cat ./testsuit/test.txt | ./py3line.py "line = re.findall(r'\b\w\w\w\b', line); if not line: continue; print(line)"
    ['cat']
    ['dog']

.. code-block:: bash

    # Regex matching with groups
    $ cat ./testsuit/test.txt | ./py3line.py "line = re.findall(r' is ([A-Z]\w*)', line); if not line: continue; print(*line)"
    Betty
    Frank
    George
    Adam

.. code-block:: bash

    # cat ./testsuit/test.txt | ./py3line.py "line = re.search(r' is ([A-Z]\w*)', line); if not line: continue; line.group(1)"
    $ cat ./testsuit/test.txt | ./py3line.py "rgx = re.compile(r' is ([A-Z]\w*)'); line = rgx.search(line); if not line: continue; print(line.group(1))"
    Betty
    Frank
    George
    Adam

.. code-block:: bash

    # head -n 2
    # cat ./testsuit/test.txt | ./py3line.py "stream = enumerate(stream); if line[0] >= 2: break; print(line[1])"
    $ cat ./testsuit/test.txt | ./py3line.py "stream = list(stream)[:2]; print(line)"
    This is my cat,
     whose name is Betty.

.. code-block:: bash

    # Print just the URLs in the access log
    $ cat ./testsuit/nginx.log | ./py3line.py "print(shlex.split(line)[13])"
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

.. code-block:: bash

    # Print most common accessed urls and filter accessed more then 5 times
    $ cat ./testsuit/nginx.log | ./py3line.py "line = shlex.split(line)[13]; stream = collections.Counter(stream).most_common(); if line[1] < 5: continue; print(line)"
    ('HEAD / HTTP/1.0', 10)

Complex examples
----------------

.. code-block:: bash

    # create directory tree
    echo -e "y1\nx2\nz3" | ./py3line.py "pathlib.Path('/DATA/' + line +'/db-backup/').mkdir(parents=True, exist_ok=True)"

    group by 3 lines ... (https://askubuntu.com/questions/1052622/separate-log-text-according-to-paragraph)

HELP
----

::

    $ ./py3line.py --help
    usage: py3line.py [-h] [-v] [-q] [--version] [--pycode]
                      [expression [expression ...]]

    Py3line is a UNIX command-line tool for a simple text stream processing by the
    Python one-liner scripts. Like grep, sed and awk.

    positional arguments:
      expression     python comma separated expressions

    optional arguments:
      -h, --help     show this help message and exit
      -v, --verbose
      -q, --quiet
      --version      print the version string
      --pycode       show generated python code

.. _Pahaz White: https://github.com/pahaz/
.. _py3line: https://pypi.python.org/pypi/py3line/
.. _pyp: https://pypi.python.org/pypi/pyp/
.. _piep: https://github.com/timbertson/piep/tree/master/piep/
.. _pysed: https://github.com/dslackw/pysed/blob/master/pysed/main.py
.. _pyline: https://github.com/westurner/pyline/blob/master/pyline/pyline.py
.. _pyfil: https://github.com/ninjaaron/pyfil