"""
Strictly speaking, signal handling and registration code can live anywhere you like, although it’s
recommended to avoid the application’s root module and its models module to minimize side-effects
of importing code.
In practice, signal handlers are usually defined in a signals submodule of the application they
relate to. Signal receivers are connected in the ready() method of your application configuration
class. If you’re using the receiver() decorator, simply import the signals submodule inside
ready().
https://stackoverflow.com/a/22924754
https://docs.djangoproject.com/en/3.2/topics/signals/
"""
