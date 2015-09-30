import itertools
import string

from unittest2 import TestCase

from feature_ramp import redis
from feature_ramp.Feature import Feature


class FeatureTest(TestCase):
    """ Tests the feature ramping system in Redis. """

    def setUp(self):
        self.feature_test = Feature("testing")

    def tearDown(self):
        for feature in Feature.all_features():
            Feature(feature).delete()

    def test_initialize_feature_with_default_percentage(self):
        feature_test = Feature("testing", default_percentage=100)

        self.assertEquals(feature_test.percentage, 100)

    def test_reset_settings(self):
        """ Tests calling reset_settings resets the correct
        data and updates it in Redis. """

        self.feature_test.set_percentage(5)
        self.feature_test.add_to_whitelist(3)
        self.feature_test.add_to_blacklist(4)
        self.feature_test.reset_settings()

        generated = Feature("testing")
        self.assertEqual(generated.percentage, 0)
        self.assertFalse(3 in generated.whitelist)
        self.assertFalse(4 in generated.blacklist)

    def test_delete(self):
        """ Tests that calling delete removes the data from Redis. """

        self.feature_test.set_percentage(5)
        self.feature_test.delete()
        key = self.feature_test._get_redis_key()
        redis_data = redis.get(key)
        self.assertTrue(redis_data is None)

        set_key = Feature._get_redis_set_key()
        self.assertFalse(redis.sismember(set_key, key))

    def test_all_features(self):
        """ Tests that the method returns a list of all feature names activated. """
        to_create = ['looktest1', 'looktest2', 'looktest3']
        for f in to_create:
            Feature(f).activate()

        all_features = Feature.all_features()
        self.assertEqual(len(all_features), len(to_create))
        for f in to_create:
            self.assertTrue(f in all_features)

    def test_all_features_with_data(self):
        """ Tests that the method returns the correct data with activated features. """
        feature1 = Feature('looktest1')
        feature1.set_percentage(5)

        feature2 = Feature('looktest2')
        feature2.activate()
        feature2.add_to_whitelist(3)

        feature3 = Feature('looktest3')
        feature3.activate()
        feature3.add_to_blacklist(4)
        feature3.add_to_blacklist(5)

        feature4 = Feature('looktest4')
        feature4.activate()
        feature4.add_to_whitelist(3)
        feature4.add_to_whitelist(5)
        feature4.add_to_blacklist(4)

        all_features = Feature.all_features(include_data=True)
        self.assertEqual(len(all_features), 4)

        for key in ['looktest1','looktest2','looktest3','looktest4']:
            self.assertTrue(key in all_features)
            if not key == 'looktest1':
                self.assertEqual(all_features[key]['percentage'], 100)

        self.assertEqual(all_features['looktest1']['percentage'], 5)
        self.assertFalse('whitelist' in all_features['looktest1'])
        self.assertFalse('blacklist' in all_features['looktest1'])

        self.assertTrue('whitelist' in all_features['looktest2'])
        self.assertEqual(all_features['looktest2']['whitelist'], [3])
        self.assertFalse('blacklist' in all_features['looktest2'])

        self.assertFalse('whitelist' in all_features['looktest3'])
        self.assertTrue('blacklist' in all_features['looktest3'])
        self.assertEqual(all_features['looktest3']['blacklist'], [4,5])

        self.assertTrue('whitelist' in all_features['looktest4'])
        self.assertEqual(all_features['looktest4']['whitelist'], [3, 5])
        self.assertTrue('blacklist' in all_features['looktest4'])
        self.assertEqual(all_features['looktest4']['blacklist'], [4])

    def test_set_add(self):
        """ Tests that creating a feature stores its key in a Redis set. """

        self.feature_test.set_percentage(15)
        key = self.feature_test._get_redis_key()
        set_key = Feature._get_redis_set_key()
        self.assertTrue(redis.sismember(set_key, key))

    def test_set_percentage(self):
        """ Tests calling set_percentage sets the correct
        data in Redis. """

        self.feature_test.set_percentage(5)
        self.assertEqual(Feature("testing").percentage, 5)

    def test_set_float_percentage(self):
        """ Tests that calling set_percentage() with a float truncates to int. """

        self.feature_test.set_percentage(50.5)
        self.assertEqual(self.feature_test.percentage, 50)

    def test_set_string_percentage(self):
        """ Tests that calling set_percentage() with a string converts it to an int if possible. """

        self.feature_test.set_percentage("50")
        self.assertEqual(self.feature_test.percentage, 50)
        self.assertTrue(isinstance(self.feature_test.percentage, int))

    def test_set_invalid_string_percentage(self):
        """ Tests that calling set_percentage() on an invalid percentage raises ValueError. """

        with self.assertRaises(ValueError):
            self.feature_test.set_percentage("meow")

    def test_add_to_whitelist(self):
        """ Tests calling add_to_whitelist sets the correct
        data in Redis. """

        self.feature_test.add_to_whitelist(3)
        self.assertTrue(3 in Feature("testing").whitelist)

    def test_add_to_whitelist_with_string(self):
        """ Tests calling add_to_whitelist sets the correct
        data in Redis when using a string. """
        email = 'example@example.com'
        self.feature_test.add_to_whitelist(email)
        self.assertTrue(email in Feature("testing").whitelist)

    def test_add_to_whitelist_with_duplicate(self):
        """ Tests calling add_to_whitelist doesn't set duplicate
        data. """

        self.feature_test.add_to_whitelist(3)
        self.feature_test.add_to_whitelist(3)
        self.assertEqual(
            len([id for id in Feature("testing").whitelist if id == 3]),
            1)

    def test_remove_from_whitelist(self):
        """ Tests calling remove_from_whitelist sets the correct
        data in Redis. """

        self.feature_test.add_to_whitelist(3)
        self.feature_test.remove_from_whitelist(3)
        self.assertFalse(3 in Feature("testing").whitelist)

    def test_remove_from_whitelist_with_string(self):
        """ Tests calling remove_from_whitelist using string sets the correct
        data in Redis. """
        email = 'example@example.com'
        self.feature_test.add_to_whitelist(email)
        self.feature_test.remove_from_whitelist(email)
        self.assertFalse(email in Feature("testing").whitelist)

    def test_add_to_blacklist(self):
        """ Tests calling add_to_blacklist sets the correct
        data in Redis. """

        self.feature_test.add_to_blacklist(3)
        self.assertTrue(3 in Feature("testing").blacklist)

    def test_add_to_blacklist_with_string(self):
        """ Tests calling add_to_blacklist sets the correct
        data in Redis when using a string. """
        email = 'example@example.com'
        self.feature_test.add_to_blacklist(email)
        self.assertTrue(email in Feature("testing").blacklist)

    def test_add_to_blacklist_with_duplicate(self):
        """ Tests calling add_to_blacklist doesn't set duplicate
        data. """

        self.feature_test.add_to_blacklist(3)
        self.feature_test.add_to_blacklist(3)
        self.assertEqual(
            len([id for id in Feature("testing").blacklist if id == 3]),
            1)

    def test_remove_from_blacklist(self):
        """ Tests calling remove_from_blacklist sets the correct
        data in Redis. """

        self.feature_test.add_to_blacklist(3)
        self.feature_test.remove_from_blacklist(3)
        self.assertFalse(3 in Feature("testing").blacklist)

    def test_remove_from_blacklist_with_string(self):
        """ Tests calling remove_from_blacklist using string sets the correct
        data in Redis. """
        email = 'example@example.com'
        self.feature_test.add_to_blacklist(email)
        self.feature_test.remove_from_blacklist(email)
        self.assertFalse(email in Feature("testing").blacklist)

    def test_active_off(self):
        """ Tests calling is_active is correct when off. """

        self.feature_test.set_percentage(0)
        self.assertFalse(self.feature_test.is_active)

    def test_active_on(self):
        """ Tests calling is_active is correct when on. """

        self.feature_test.set_percentage(100)
        self.assertTrue(self.feature_test.is_active)

    def test_visible_whitelisted(self):
        """ Tests calling is_visible is correct when whitelisted. """

        self.feature_test.set_percentage(0)
        self.feature_test.add_to_whitelist(3)
        self.assertTrue(self.feature_test.is_visible(3))

    def test_visible_whitelisted_with_string(self):
        """ Tests calling is_visible with string is correct when whitelisted. """
        email = 'example@example.com'
        self.feature_test.set_percentage(0)
        self.feature_test.add_to_whitelist(email)
        self.assertTrue(self.feature_test.is_visible(email))

    def test_visible_blacklisted(self):
        """ Tests calling is_visible is correct when blacklisted. """

        self.feature_test.set_percentage(100)
        self.feature_test.add_to_blacklist(3)
        self.assertFalse(self.feature_test.is_visible(3))

    def test_visible_blacklisted_with_string(self):
        """ Tests calling is_visible with string is correct when blacklisted. """
        email = 'example@example.com'
        self.feature_test.set_percentage(0)
        self.feature_test.add_to_blacklist(email)
        self.assertFalse(self.feature_test.is_visible(email))

    def test_visible_white_and_blacklisted(self):
        """ Tests calling is_visible is correct when both white and blacklisted. """

        self.feature_test.set_percentage(0)
        self.feature_test.add_to_whitelist(3)
        self.feature_test.add_to_blacklist(3)
        self.assertTrue(self.feature_test.is_visible(3))

    def test_visible_white_and_blacklisted_with_string(self):
        """ Tests calling is_visible is correct when both white and blacklisted. """
        email = 'example@example.com'
        self.feature_test.set_percentage(0)
        self.feature_test.add_to_whitelist(email)
        self.feature_test.add_to_blacklist(email)
        self.assertTrue(self.feature_test.is_visible(email))

    def test_visible_ramp(self):
        """ Tests calling is_visible is correct when partially ramped. """
        total_number = 100000
        expected_percentage = .10
        self.feature_test.set_percentage(expected_percentage * 100)
        # Generate a range of user ids and map these ids to the feature
        # test result.
        user_ids = range(1, total_number + 1)
        visibility_map = [
            self.feature_test.is_visible(user_id)
            for user_id
            in user_ids
        ]
        # Count the number of success conditions.
        visibility_count = visibility_map.count(True)
        # This should match 10%.
        actual_percentage = visibility_count / float(total_number)
        self.assertAlmostEqual(actual_percentage, expected_percentage, delta=.012)

    def test_visible_ramp_using_string(self):
        """Tests calling is_visible when using string as identifier is
        correct when partially ramped.
        """
        identifiers = list(itertools.product(string.lowercase, repeat=3))
        total_number = len(identifiers)
        expected_percentage = .10
        self.feature_test.set_percentage(expected_percentage * 100)
        # Generate a range of user ids and map these ids to the feature
        # test result.
        visibility_map = [self.feature_test.is_visible(identifier)
                          for identifier in identifiers]
        # Count the number of success conditions.
        visibility_count = visibility_map.count(True)
        # This should match 10%.
        actual_percentage = visibility_count / float(total_number)
        self.assertAlmostEqual(actual_percentage, expected_percentage, delta=.012)

    def test_is_ramped_using_int(self):
        """Tests that _is_ramped accepts integers as identifer."""
        self.feature_test.set_percentage(100)
        self.assertTrue(self.feature_test._is_ramped(5))


    def test_is_ramped_using_string(self):
        """Tests that _is_ramped accepts strings as identifier."""
        self.feature_test.set_percentage(100)
        self.assertTrue(self.feature_test._is_ramped('example@example.com'))

    def test_is_ramped_using_unicode_string(self):
        """Tests that _is_ramped accepts unicode strings as identifier."""
        self.feature_test.set_percentage(100)
        self.assertTrue(self.feature_test._is_ramped(u'\u2665@example.com'))

    def test_redis_key(self):
        """ Tests the redis key builder returns the expected string. """

        generated = self.feature_test._get_redis_key()
        expected = "feature.1.testing"
        self.assertEqual(generated, expected)

    def test_group_names(self):
        feature_one = Feature('feature_one', feature_group_name='test_group')
        feature_two = Feature('feature_two', feature_group_name='test_group')

        feature_one.set_percentage(10)
        feature_two.set_percentage(10)

        identifiers = range(1, 10001)

        visibility_test_one = [id for id in identifiers
                                if feature_one.is_visible(id)]

        visibility_test_two = [id for id in identifiers
                                if feature_two.is_visible(id)]

        self.assertEqual(visibility_test_one, visibility_test_two)
