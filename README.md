# Feature Ramp
[![Build Status](https://travis-ci.org/venmo/feature_ramp.svg?branch=master)](https://travis-ci.org/venmo/feature_ramp)

Supports [feature toggling](http://martinfowler.com/bliki/FeatureToggle.html) and ramping features via a lightweight Redis backend.

Installation
------------------
Feature ramp requires requires a running Redis server. If your application is written in Python, we recommend using [redis-py](https://github.com/andymccurdy/redis-py) for a convenient way to interface with Redis. To install Redis, follow the [Redis Quick Start](http://redis.io/topics/quickstart).

Once you have redis-py and a Redis server running, you're ready to start using Feature Ramp.

Getting Started
-----------------
``` python
>>> from feature_ramp.Feature import Feature
>>> feature_a = Feature('feature_a')
>>> feature_a.activate()
>>> feature_a.is_active
True
>>> feature_a.deactivate()
>>> feature_a.is_active
False
```
