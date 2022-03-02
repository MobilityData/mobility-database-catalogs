from unittest import TestCase, skip
from unittest.mock import patch, Mock
from tools.representations import Catalog, FILENAME


class TestCatalog(TestCase):
    def setUp(self):
        self.test_path = "some_path"
        self.test_filename = "some-source.json"
        self.test_another_filename = "another-source.json"
        self.test_key = "some_key"
        self.test_value = "some_value"
        self.test_another_value = "another_value"
        self.test_obj = {self.test_key: self.test_value}
        self.test_another_obj = {self.test_key: self.test_another_value}

    @patch("tools.representations.os.walk")
    def test_identify(self, mock_walk):
        mock_walk.return_value = [
            ("/catalogs", ("sources",), ()),
            ("/catalogs/sources", ("gtfs",), ()),
            ("/catalogs/sources/gtfs", ("schedule",), ()),
            (
                "/catalogs/sources/gtfs/schedule",
                (),
                (self.test_filename, self.test_another_filename),
            ),
        ]
        under_test = Catalog.identify(catalog_root=self.test_path)
        self.assertEqual(under_test, 3)
        self.assertEqual(mock_walk.call_count, 1)

    @patch("tools.representations.os.walk")
    @patch("tools.representations.os.path.join")
    @patch("tools.representations.open")
    @patch("tools.representations.json.load")
    def test_aggregate(self, mock_json, mock_open, mock_path, mock_walk):
        mock_walk.return_value = [
            ("/catalogs", ("sources",), ()),
            ("/catalogs/sources", ("gtfs",), ()),
            ("/catalogs/sources/gtfs", ("schedule",), ()),
            (
                "/catalogs/sources/gtfs/schedule",
                (),
                (self.test_filename, self.test_another_filename),
            ),
        ]
        mock_json.side_effect = [self.test_obj, self.test_another_obj]
        under_test = Catalog.aggregate(
            catalog_path=self.test_path, id_key=self.test_key, entity_cls=dict
        )
        self.assertEqual(
            under_test,
            {
                self.test_value: {
                    FILENAME: self.test_filename,
                    self.test_key: self.test_value,
                },
                self.test_another_value: {
                    FILENAME: self.test_another_filename,
                    self.test_key: self.test_another_value,
                },
            },
        )
        self.assertEqual(mock_walk.call_count, 1)
        self.assertEqual(mock_path.call_count, 2)
        self.assertEqual(mock_open.call_count, 2)
        self.assertEqual(mock_json.call_count, 2)
