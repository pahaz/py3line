More complex examples:

1. We want to know list of IP addresses connected to our SSH port.

Tipical bash one-liner:

netstat -tn 2>/dev/null | grep :22 | awk '{print $5}' | cut -d: -f1 | uniq -c | sort -nr | head

The same with py3line:

netstat -tn 2>/dev/null | py3line "x if ':22' in x else skip" | py3line "x.split()[4]" | py3line "x.split(':')[0]" | py3line -m collections "collections.Counter(xx).most_common(20)"

or easier:

netstat -tn 2>/dev/null | py3line -m collections "x if ':22' in x else skip; x.split()[4].split(':')[0]; collections.Counter(xx).most_common(20)"

