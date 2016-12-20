Internals of Sacred
*******************
This section is meant as a reference for Sacred developers.
It should give a high-level description of some of the more intricate
internals of Sacred.


Configuration Process
=====================
The configuration process is executed when an experiment is started, and
determines the final configuration that should be used for the run:

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



