A Lesson in Scaling 6LoWPAN - Minimal Fragment Forwarding in Lossy Networks
===========================================================================

Code and documentation to reproduce our experiment results

Code
----

The explicit RIOT version is included as a submodule in this repository
(`RIOT`). It is based on the 2019.07 release of RIOT but also contains all
relevant changes to conduct the experiments. The PRs these changes came from are
documented within the git history. For more information use

```sh
cd RIOT
git log
```

The `apps` directory contains the RIOT applications required for the
experiments. Please refer to their `README`s for their usage.

The `scripts` directory contains both scripts for [measuring the testbed as
described in Section IV-A of the paper](./scripts/testbed_measure), to [conduct
the experiments](./scripts/experiment_ctrl), and to [plot their
results](./scripts/plots). Please also refer to their respective `README`s for
their usage.

To handle the rather specific dependencies of the scripts, we recommend using
[virtualenv]:

```sh
virtualenv -p python3 env
source env/bin/activate
```

[virtualenv]: https://virtualenv.pypa.io/en/latest/

Documentation
-------------
TODO: link paper once it is published
