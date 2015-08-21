# Feature Ramp
[![Build Status](https://travis-ci.org/venmo/feature_ramp.svg?branch=master)](https://travis-ci.org/venmo/feature_ramp)

Supports [feature toggling](http://martinfowler.com/bliki/FeatureToggle.html) and ramping features via a lightweight Redis backend.

Installation
------------------
Feature ramp requires requires a running Redis server. If your application is written in Python, we recommend using [redis-py](https://github.com/andymccurdy/redis-py) for a convenient way to interface with Redis. To install Redis, follow the [Redis Quick Start](http://redis.io/topics/quickstart).

Once you have redis-py and a Redis server running, you're ready to start using Feature Ramp.

NOTE: Feature Ramp assumes your Redis server is running at localhost on port 6379 (this is the default redis-py configuration). To customize this, make the necessary edits [here](https://github.com/venmo/feature_ramp/blob/8a49785961fcbb01299329e9a1a994ed6a7b4f34/feature_ramp/__init__.py#L3).

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
