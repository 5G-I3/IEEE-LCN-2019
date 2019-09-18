A Lesson in Scaling 6LoWPAN - Minimal Fragment Forwarding in Lossy Networks
===========================================================================

Code and documentation to reproduce our experiment results

Code
----

The explicit RIOT version is included as a submodule in this repository
(`RIOT`).

The `apps` directory contains the RIOT applications required for the
experiments. Please refer to their `README`s for their usage.

The `scripts` directory contains both scripts for measuring the testbed as
described in Section IV-A of the paper and to conduct the experiments.
Please also refer to their respective `README`s for their usage.

To handle the rather specific dependencies, we recommend using [virtualenv]:

```
virtualenv -p python3 env
source env/bin/activate
```

TODO: provide scripts for plotting

[virtualenv]: https://virtualenv.pypa.io/en/latest/

Documentation
-------------
TODO: link paper once it is published
