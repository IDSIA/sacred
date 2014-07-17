Observing an Experiment
***********************
When you run an experiment you want to keep track of enough information,
such that you can analyse the results, and even reproduce them if needed.
The way ``sacred`` helps you doing that is by making letting you attach
*Observers* to your experiment.

- assume a local MongoDB (link to instructions)

  >>> TODO: MongoDB example

What is being observed
======================

    - run_created_event
        * name, doc, mainfile, dependencies, host_info
    - started_event
        * start_time, config
    - heartbeat_event
        * info, captured_out
    - completed_event
        * stop_time, result
    - interrupted_event
        * interrupt_time
    - failed_event
        * fail_time, fail_trace

The MongoDB Observer
====================

   - explain this standard observer.
   - assume a local MongoDB (link to instructions)
   - how to attach it from code / from commandline
   - what does it do?

Saving Custom ``info``
======================

just edit ex.info while it is running
