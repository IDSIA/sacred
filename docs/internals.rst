Internals of Sacred
*******************
Here I'll describe some internals of Sacred.


Configuration Process
=====================
The configuration process is run when an experiment is started:

 #. Determine the order for running the ingredients

    - topological
    - in the order they where added

 #. For each ingredient do:

    - gather all config updates that apply (needs ``config_updates``)
    - gather all named configs to use (needs ``named_configs``)
    - gather all fallbacks that apply from subrunners (needs ``subrunners.config``)
    - make the fallbacks read-only
    - run all named configs and use the results as additional config updates,
      but with lower priority than the global ones. (needs ``named_configs``, ``config_updates``)
    - run all normal configs
    - update the global ``config``
    - run the config hook
    - update the global ``config_updates``



