"""Unit tests for the collection serializers.

Tests cover:
- CollectionMetadataSerializer.get_tags method
"""
from unittest.mock import Mock
from django.test import TestCase

from galaxy_ng.app.api.ui.v1.serializers.collection import CollectionMetadataSerializer


class TestCollectionMetadataSerializerGetTags(TestCase):
    """Test the get_tags method of CollectionMetadataSerializer.

    The get_tags method was updated to work with tags as an ArrayField
    (list of strings) instead of a ForeignKey relation to a Tag model.
    """

    def setUp(self):
        # Create a serializer instance with mock context
        self.serializer = CollectionMetadataSerializer(context={'request': Mock()})

    def test_get_tags_with_list(self):
        """Test get_tags returns tags when collection_version has tags as list."""
        mock_cv = Mock()
        mock_cv.tags = ['networking', 'database', 'security']

        result = self.serializer.get_tags(mock_cv)

        assert result == ['networking', 'database', 'security']

    def test_get_tags_with_empty_list(self):
        """Test get_tags returns empty list when tags is empty."""
        mock_cv = Mock()
        mock_cv.tags = []

        result = self.serializer.get_tags(mock_cv)

        assert result == []

    def test_get_tags_with_none(self):
        """Test get_tags returns empty list when tags is None."""
        mock_cv = Mock()
        mock_cv.tags = None

        result = self.serializer.get_tags(mock_cv)

        assert result == []

    def test_get_tags_with_dict_input(self):
        """Test get_tags handles dict input (from aggregated querysets)."""
        # When using .values() or annotated querysets, the object may be a dict
        cv_dict = {
            'tags': ['cloud', 'aws', 'infrastructure'],
            'name': 'test_collection',
        }

        result = self.serializer.get_tags(cv_dict)

        assert result == ['cloud', 'aws', 'infrastructure']

    def test_get_tags_with_dict_empty_tags(self):
        """Test get_tags handles dict input with empty tags."""
        cv_dict = {
            'tags': [],
            'name': 'test_collection',
        }

        result = self.serializer.get_tags(cv_dict)

        assert result == []

    def test_get_tags_with_dict_missing_tags(self):
        """Test get_tags handles dict input without tags key."""
        cv_dict = {
            'name': 'test_collection',
        }

        result = self.serializer.get_tags(cv_dict)

        assert result == []

    def test_get_tags_with_single_tag(self):
        """Test get_tags works with single tag."""
        mock_cv = Mock()
        mock_cv.tags = ['monitoring']

        result = self.serializer.get_tags(mock_cv)

        assert result == ['monitoring']

    def test_get_tags_preserves_order(self):
        """Test get_tags preserves tag order."""
        mock_cv = Mock()
        mock_cv.tags = ['z_last', 'a_first', 'm_middle']

        result = self.serializer.get_tags(mock_cv)

        # Order should be preserved as-is
        assert result == ['z_last', 'a_first', 'm_middle']

    def test_get_tags_with_special_characters(self):
        """Test get_tags handles tags with special characters."""
        mock_cv = Mock()
        mock_cv.tags = ['web-server', 'database_admin', 'cloud.aws']

        result = self.serializer.get_tags(mock_cv)

        assert result == ['web-server', 'database_admin', 'cloud.aws']
