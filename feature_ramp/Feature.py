import json
# import redis

class Feature(object):
    """
    A class to control ramping features to a percentage of users
    without needing to deploy to change the ramp.

    Usage:

    Feature("on_off_toggled").activate()
    Feature("on_off_toggled").is_active
    Feature("on_off_toggled").deactivate()

    Feature("all_functionality").set_percentage(5)
    Feature("all_functionality").add_to_whitelist(identifier)
    Feature("all_functionality").is_visible(identifier)
    Feature("all_functionality").remove_from_whitelist(identifier)
    Feature("all_functionality").deactivate()

    Feature("go_away").reset_settings()
    Feature("go_away").delete()
    """

    REDIS_NAMESPACE = 'feature'
    REDIS_VERSION = 1
    REDIS_SET_KEY = 'active_features'

    def __init__(self, feature_name, feature_group_name=None, default_percentage=0):
        self.feature_name = feature_name  # set here so redis_key() works
        self.feature_group_name = feature_group_name

        key = self._get_redis_key()
        redis_raw = redis.get(key)
        redis_data = self._deserialize(redis_raw)

        self.whitelist = redis_data.get('whitelist', [])
        self.blacklist = redis_data.get('blacklist', [])
        self.percentage = redis_data.get('percentage', default_percentage)

    def is_visible(self, identifier):
        """ Returns true if the feature is visible to the given identifier.
        Whitelisted users are always on even if they are also blacklisted.
        Blacklisted users are always off unless whitelisted.
        For users neither white or blacklisted, it will respect ramp percentage.
        """

        if self.is_whitelisted(identifier):
            return True

        if self.is_blacklisted(identifier):
            return False

        return self._is_ramped(identifier)

    @property
    def is_active(self):
        """ Returns true if a single-toggle feature is on or off.
        Similar to is_visible() but does not require an identifier.
        """

        return self.percentage > 0

    def is_whitelisted(self, identifier):
        """ Given a identifier, returns true if the id is present in the whitelist. """

        return identifier in self.whitelist

    def is_blacklisted(self, identifier):
        """ Given a identifier, returns true if the id is present in the blacklist. """

        return identifier in self.blacklist

    def _is_ramped(self, identifier):
        """
        Checks whether ``identifier`` is ramped for this feature or not.
        ``identifier`` can be a user_id, email address, etc

        Warning: This method ignores white- and blacklists. For
        completeness, you probably want to use is_visible().

        Users are ramped for features by this method in a deterministic
        way, such that the same set of users will be ramped
        consistently for the same feature across multiple requests.
        However, different features will have different sets of users
        ramped, so that the same set of users aren't always the ones
        getting the first percent of experimental changes (e.g.,
        user.id in {1, 101, 202, ...}). To achieve this, whether or not
        this user is ramped is computed by hashing the feature name and
        combining this hash with the user's integer id, using the
        modulus operator to distribute the results evenly on a scale
        of 0 to 100.

        Returns True if the feature is ramped high enough that the
        feature should be visible to the user with that id, and False
        if not.
        """
        consistent_offset = hash(self.feature_name) % 100 if not self.feature_group_name else hash(self.feature_group_name)
        identifier = identifier if isinstance(identifier, basestring) else str(identifier)
        ramp_ranking = (consistent_offset + hash(identifier)) % 100

        return ramp_ranking < self.percentage

    def activate(self):
        """ Ramp feature to 100%. This is a convenience method useful for single-toggle features. """

        self.set_percentage(100)

    def deactivate(self):
        """ Ramp feature to 0%. This is a convenience method useful for single-toggle features. """

        self.set_percentage(0)

    def reset_settings(self):
        """ Clears all settings for the feature. The feature is deactivated and
        the whitelist and blacklist are emptied.
        """

        self.percentage = 0
        self.whitelist = []
        self.blacklist = []
        self._save()

    def delete(self):
        """ Deletes the feature settings from Redis entirely. """

        key = self._get_redis_key()
        redis.delete(key)
        redis.srem(Feature._get_redis_set_key(), key)

    def set_percentage(self, percentage):
        """ Ramps the feature to the given percentage.

        If percentage is not a number between 0 and 100 inclusive, ValueError is raised.
        Calls int() on percentage because we are using modulus to select the users
        being shown the feature in _is_ramped(); floats will truncated.
        """

        percentage = int(float(percentage))
        if (percentage < 0 or percentage > 100):
            raise ValueError("Percentage is not a valid integer")

        self.percentage = percentage
        self._save()

    def add_to_whitelist(self, identifier):
        """ Whitelist the given identifier to always see the feature regardless of ramp. """

        self.whitelist.append(identifier)
        self._save()

    def remove_from_whitelist(self, identifier):
        """ Remove the given identifier from the whitelist to respect ramp percentage. """

        self.whitelist.remove(identifier)
        self._save()

    def add_to_blacklist(self, identifier):
        """ Blacklist the given identifier to never see the feature regardless of ramp. """

        self.blacklist.append(identifier)
        self._save()

    def remove_from_blacklist(self, identifier):
        """ Remove the given identifier from the blacklist to respect ramp percentage. """

        self.blacklist.remove(identifier)
        self._save()

    @classmethod
    def all_features(cls, include_data=False):
        """
        Returns a list of all active feature names.

        With an optional flag, this method will instead return a dict with
        ramping data for the feature included.

        Example ramping data:
        { 'feature_name':
            { 'percentage': 50, 'whitelist': [3], 'blacklist': [4,5] }
        }
        """
        key = cls._get_redis_set_key()
        features = [cls._get_feature_name_from_redis_key(rkey) for rkey in redis.smembers(key)]
        if not include_data:
            return features

        # we intentionally do not use pipelining here, since that would lock Redis and
        # this does not need to be atomic
        features_with_data = dict()
        for feature in features:
            data = cls(feature)
            features_with_data[feature] = {'percentage': data.percentage}
            if data.whitelist:
                features_with_data[feature]['whitelist'] = data.whitelist
            if data.blacklist:
                features_with_data[feature]['blacklist'] = data.blacklist

        return features_with_data

    def _save(self):
        """ Saves the feature settings to Redis in a dictionary. """

        key = self._get_redis_key()
        value = json.dumps(self._get_redis_data())
        redis.set(key, value)

        # store feature key in a set so we know what's turned on without
        # needing to search all Redis keys with a * which is slow.
        set_key = Feature._get_redis_set_key()
        redis.sadd(set_key, key)

    def _get_redis_key(self):
        """ Returns the key used in Redis to store a feature's information, with namespace. """

        return '{0}.{1}.{2}'.format(Feature.REDIS_NAMESPACE,
                                    Feature.REDIS_VERSION,
                                    self.feature_name)

    @classmethod
    def _get_feature_name_from_redis_key(self, key):
        """ Returns the feature name given the namespaced key used in Redis. """
        return key.split('.')[-1]

    @classmethod
    def _get_redis_set_key(cls):
        """ Returns the key used in Redis to store a feature's information, with namespace. """

        return '{0}.{1}'.format(Feature.REDIS_NAMESPACE,
                                Feature.REDIS_SET_KEY)

    def _get_redis_data(self):
        """ Returns the dictionary representation of this object for storage in Redis. """

        return {
            'whitelist': self.whitelist,
            'blacklist': self.blacklist,
            'percentage': self.percentage
        }

    def _deserialize(self, redis_obj):
        """ Deserializes the serialized JSON representation of this object's dictionary
        from Redis. If no object is provided, it returns an empty dictionary.
        """

        if redis_obj is None:
            return {}

        return json.loads(redis_obj)

    def __str__(self):
        """ Pretty print the feature and some stats """
        stats = self._get_redis_data()
        return "Feature: {0}\nwhitelisted: {1}\nblacklisted: {2}\npercentage: {3}\n".format(self.feature_name, stats['whitelist'], stats['blacklist'], stats['percentage'])
