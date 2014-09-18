Sacred
======

> Every experiment is sacred<br>
> Every experiment is great<br>
> If a experiment is wasted<br>
> God gets quite irate<br>


Sacred is a tool to help you configure, organize, log and reproduce experiments.
It is designed to do all the tedious overhead work that you need to do around 
your actual experiment in order to:

 * keep track of all the parameters of your experiment
 * easily run your experiment for different settings
 * save configurations for individual runs in a database
 * reproduce your results

In Sacred we achieve this through the following main mechanisms:

 * **ConfigScopes**: A very convenient way of the local variables in a function
   to define the parameters your experiment uses.
 * **Config Injection**: You can access all parameters of your configuration
   from every function. They are automatically injected by name. 
 * **Command-line interface**: You get a powerful command-line interface for each
   experiment that you can use to change parameters and run different variants.
 * **Observers**: Sacred provides Observers that log all kinds of information 
   about your experiment, its dependencies, the configuration you used, 
   the machine it is run on, and of course the result. These can be saved
   to a MongoDB, for easy access later.
 * **Automatic seeding** helps controlling the randomness in your experiments, 
   such that the results remain reproducible.
 

Documentation
-------------
The documentation is hosted at [ReadTheDocs](http://sacred.readthedocs.org/).

Installing
----------
You can directly install it from the Python Package Index with pip:

    pip install sacred

Or if you want to do it manually you can checkout the current version from git
and install it yourself:

    git clone https://github.com/Qwlouse/sacred.git
    cd sacred
    python setup.py install

You might want to also install the `numpy` and the `pymongo` packages. They are 
optional dependencies but they offer some cool features:

    pip install numpy, pymongo
    

License
-------
This project is released under the terms of the 
[MIT license](http://opensource.org/licenses/MIT). 
