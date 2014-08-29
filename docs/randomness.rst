Controlling Randomness
**********************

  - Randomness is important for many experiments
  - but reproducibility is important too
  - so we need to be able to fix the randomness => seeds

sacred helps you with that:

  * auto-generate a seed for each experiment as part of your configuration
  * provide possibility to generate a seed for each captured function call
  * all those seeds depend deterministically on the global seed
  * that seed can be fixed easily ``>>./experiment.py with seed=123``
  * hierarchical seeding for ingredients: you fix the seed for a ingredient and all the
    sub-ingredient seeds will be fixed too




