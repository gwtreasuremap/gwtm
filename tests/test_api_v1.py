import json
import unittest
from datetime import datetime
import geoalchemy2
from unittest.mock import patch, MagicMock

from src import models, api_v1
from src.api_v1 import app, initial_request_parse, make_response
from src.enums import pointing_status, depth_unit, bandpass
from src.models import instrument, gw_alert, users, gw_candidate

INSTRUMENT_ID = 1
INSTRUMENT_NAME = 'test_instrument'
FOOTPRINT = 'test footprint'


def define_mock_pointing():
    # Create a mock pointing object
    mock_pointing = {
        "status": pointing_status.completed,
        "instrumentid": '1',
        "position": "POINT(1 1)",
        "galaxy_catalog": 123,
        "galaxy_catalogid": 456,
        "depth": 20.5,
        "depth_err": 0.5,
        "depth_unit": depth_unit.ab_mag,
        "time": datetime.now().isoformat(),
        "datecreated": datetime.now().isoformat(),
        "dateupdated": datetime.now().isoformat(),
        "submitterid": 1234,
        "pos_angle": 45.0,
        "band": bandpass.U,
        "central_wave": 500.0,
        "bandwidth": 50.0
    }

    return mock_pointing

class ApiV1Tests(unittest.TestCase):


    @classmethod
    def setUpClass(cls):
        # Set up a test client for the application
        cls.client = app.test_client()
        # Set a valid token for authentication in tests
        cls.valid_token = 'valid_token'

    def setUp(self):
        # Mock the dump_json function to avoid actual JSON dumping during tests
        api_v1.dump_json = MagicMock()

        # Mock footprint object with parsed data
        self.footprint = MagicMock(
            parse={'instrumentid': INSTRUMENT_ID, 'name': INSTRUMENT_NAME, 'footprint': FOOTPRINT})
        # Mock user object with an ID
        self.user = MagicMock(id=1234)
        # Mock galaxy list object with an ID and submitter ID
        self.galaxy_list = MagicMock(id=1, submitterid=1234)
        # Mock GW alert object with a graceid
        self.mock_gw_alert = MagicMock(graceid='graceid')
        # Set a valid timestamp for timesent
        self.valid_timesent_stamp = '2019-05-01T12:00:00.00'
        # Mock valid galaxies data
        self.valid_galaxies = [
            {'ra': 0.0, 'dec': 0.0, 'score': 0.0, 'name': 'test_name', 'rank': 123, 'groupname': 'test_group'}]
        # Mock galaxy entry object
        self.galaxy_entry = [MagicMock()]
        # Mock valid candidate data
        self.valid_candidate_data = MagicMock(id='valid_candidate_id')

    @patch('src.api_v1.db')
    def test_initial_request_parse_valid_json(self, mock_db):
        # Mock request object with valid JSON data
        mock_request = MagicMock()
        mock_request.get_json.return_value = {'api_token': 'valid_token'}
        # Mock database query to return a valid user
        mock_db.session.query().filter().first.return_value = MagicMock()
        # Call the function to test with the mocked request
        valid, message, args, user = initial_request_parse(mock_request, only_json=True)
        # Assert that the function returns valid results
        self.assertTrue(valid)
        self.assertEqual(message, '')
        self.assertIsNotNone(args)
        self.assertIsNotNone(user)

    @patch('src.api_v1.db')
    def test_initial_request_parse_invalid_json(self, mock_db):
        # Mock request object to raise an exception when getting JSON data
        mock_request = MagicMock()
        mock_request.get_json.side_effect = Exception()
        # Call the function to test with the mocked request
        valid, message, args, user = initial_request_parse(mock_request, only_json=True)
        # Assert that the function returns invalid results
        self.assertFalse(valid)
        self.assertEqual(message, 'Endpoint only accepts json argument parameters')
        self.assertIsNone(args)
        self.assertIsNone(user)

    @patch('src.api_v1.db')
    def test_initial_request_parse_missing_token(self, mock_db):
        mock_request = MagicMock()
        mock_request.get_json.return_value = {}
        valid, message, args, user = initial_request_parse(mock_request, only_json=True)
        self.assertFalse(valid)
        self.assertEqual(message, 'api_token is required')
        self.assertIsNotNone(args)
        self.assertIsNone(user)

    @patch('src.api_v1.db')
    def test_make_response_valid(self, mock_db):
        response = make_response('Success', 200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.response, [b'Success'])

    @patch('src.api_v1.db')
    def test_make_response_invalid(self, mock_db):
        response = make_response('Error', 500)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.response, [b'Error'])

    @patch('src.api_v1.db')
    def test_valid_request_returns_footprints(self, mock_db):
        response = self.client.get('/api/v1/footprints?api_token=token',
                                   headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    @patch('src.api_v1.db')
    def test_invalid_request_returns_error(self, mock_db):
        response = self.client.get('/api/v1/footprints')
        self.assertEqual(response.status_code, 500)

    @patch('src.api_v1.db')
    def test_valid_id_returns_correct_footprint(self, mock_db):
        mock_db.session.query().filter().all.return_value = [self.footprint]
        response = self.client.get(f'/api/v1/footprints?id={self.footprint.instrumentid}&api_token=token',
                                   headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 1)
        self.assertEqual(response.json[0]['instrumentid'], INSTRUMENT_ID)

    @patch('src.api_v1.db')
    def test_valid_name_returns_correct_footprint(self, mock_db):
        mock_db.session.query().filter().all.return_value = [self.footprint]
        response = self.client.get(f'/api/v1/footprints?name={INSTRUMENT_NAME}&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.json), 0)
        self.assertTrue(any(fp['instrumentid'] == INSTRUMENT_ID for fp in response.json))

    @patch('src.api_v1.db')
    def test_invalid_id_returns_empty_list(self, mock_db):
        response = self.client.get('/api/v1/footprints?id=9999&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 0)

    @patch('src.api_v1.db')
    def test_invalid_name_returns_empty_list(self, mock_db):
        response = self.client.get('/api/v1/footprints?name=nonexistent&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 0)

    @patch('src.api_v1.db')
    def test_valid_listid_deletes_galaxy_list(self, mock_db):
        mock_db.session.query().filter().first.side_effect = [self.user, self.galaxy_list]
        response = self.client.post('/api/v1/remove_event_galaxies', json={'listid': self.galaxy_list.id, 'api_token': self.valid_token}, headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode(), 'Successfully deleted your galaxy list')

    @patch('src.api_v1.db')
    def test_invalid_listid_returns_error(self, mock_db):
        response = self.client.post('/api/v1/remove_event_galaxies', json={'listid': 'invalid', 'api_token': self.valid_token}, headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'Invalid listid')

    @patch('src.api_v1.db')
    def test_missing_listid_returns_error(self, mock_db):
        response = self.client.post('/api/v1/remove_event_galaxies', json={'api_token': self.valid_token}, headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'Event galaxy listid is required')

    @patch('src.api_v1.db')
    def test_unauthorized_user_returns_error(self, mock_db):
        self.galaxy_list.submitterid = 9999
        mock_db.session.query().filter().first.side_effect = [self.user, self.galaxy_list]
        response = self.client.post('/api/v1/remove_event_galaxies', json={'listid': self.galaxy_list.id, 'api_token': self.valid_token}, headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'You can only delete information related to your api_token! shame shame')

    @patch('src.api_v1.db')
    def test_non_existent_listid_returns_error(self, mock_db):
        mock_db.session.query().filter().first.side_effect = [self.user, None]
        response = self.client.post('/api/v1/remove_event_galaxies', json={'listid': 9999, 'api_token': self.valid_token}, headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'No galaxies with that listid')

    @patch('src.api_v1.db')
    def test_valid_graceid_returns_galaxy_entries(self, mock_db):
        models.db = mock_db
        mock_db.session.query().filter().all.side_effect = [self.mock_gw_alert, self.galaxy_entry]
        response = self.client.get('/api/v1/event_galaxies?graceid=valid_graceid&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

    @patch('src.api_v1.db')
    def test_invalid_timesent_stamp_returns_error(self, mock_db):
        models.db = mock_db
        response = self.client.get('/api/v1/event_galaxies?graceid=valid_graceid&timesent_stamp=invalid&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), "Error parsing date. Should be %Y-%m-%dT%H:%M:%S.%f format. e.g. 2019-05-01T12:00:00.00")

    @patch('src.api_v1.db')
    def test_valid_timesent_stamp_returns_galaxy_entries(self, mock_db):
        models.db = mock_db
        mock_db.session.query().filter().all.side_effect = [self.mock_gw_alert, self.galaxy_entry]
        response = self.client.get('/api/v1/event_galaxies?graceid=valid_graceid&timesent_stamp=2019-05-01T12:00:00.00&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

    @patch('src.api_v1.db')
    def test_invalid_listid_returns_error(self, mock_db):
        models.db = mock_db
        response = self.client.get('/api/v1/event_galaxies?graceid=valid_graceid&listid=invalid&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'Invalid \'listid\'')

    @patch('src.api_v1.db')
    def test_valid_listid_returns_galaxy_entries(self, mock_db):
        models.db = mock_db
        mock_db.session.query().filter().all.side_effect = [self.mock_gw_alert, self.galaxy_entry]
        response = self.client.get('/api/v1/event_galaxies?graceid=valid_graceid&listid=1&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

    @patch('src.api_v1.db')
    def test_valid_groupname_returns_galaxy_entries(self, mock_db):
        models.db = mock_db
        mock_db.session.query().filter().all.side_effect = [self.mock_gw_alert, self.galaxy_entry]
        response = self.client.get('/api/v1/event_galaxies?graceid=valid_graceid&groupname=test_group&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

    @patch('src.api_v1.db')
    def test_valid_score_gt_returns_galaxy_entries(self, mock_db):
        models.db = mock_db
        mock_db.session.query().filter().all.side_effect = [self.mock_gw_alert, self.galaxy_entry]
        response = self.client.get('/api/v1/event_galaxies?graceid=valid_graceid&score_gt=0.5&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

    @patch('src.api_v1.db')
    def test_valid_score_lt_returns_galaxy_entries(self, mock_db):
        models.db = mock_db
        mock_db.session.query().filter().all.side_effect = [self.mock_gw_alert, self.galaxy_entry]
        response = self.client.get('/api/v1/event_galaxies?graceid=valid_graceid&score_lt=1.5&api_token=token', headers={'Authorization': f'Bearer {self.valid_token}'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

    @patch('src.api_v1.db')
    def test_post_event_galaxies_v1_valid_request(self, mock_db):
        models.db = mock_db
        mock_db.session.query().filter().all.return_value = [MagicMock()]
        response = self.client.post('/api/v1/event_galaxies', json={
            'api_token': 'token',
            'graceid': 'valid_graceid',
            'timesent_stamp': self.valid_timesent_stamp,
            'galaxies': self.valid_galaxies
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Successful adding of', response.data.decode())

    @patch('src.api_v1.db')
    def test_post_event_galaxies_v1_invalid_api_token(self, mock_db):
        models.db = mock_db
        mock_db.session.query(models.users).filter(models.users.api_token == 'invalid').first.return_value = None
        response = self.client.post('/api/v1/event_galaxies', json={
            'api_token': 'invalid',
            'graceid': 'valid_graceid',
            'timesent_stamp': self.valid_timesent_stamp,
            'galaxies': self.valid_galaxies
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'invalid api_token')

    @patch('src.api_v1.db')
    def test_post_event_galaxies_v1_missing_api_token(self, mock_db):
        models.db = mock_db
        response = self.client.post('/api/v1/event_galaxies', json={
            'graceid': 'valid_graceid',
            'timesent_stamp': self.valid_timesent_stamp,
            'galaxies': self.valid_galaxies
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'api_token is required')

    @patch('src.api_v1.db')
    def test_post_event_galaxies_v1_invalid_graceid(self, mock_db):
        models.db = mock_db
        response = self.client.post('/api/v1/event_galaxies', json={
            'api_token': 'valid_api_token',
            'graceid': 'invalid_graceid',
            'timesent_stamp': self.valid_timesent_stamp,
            'galaxies': self.valid_galaxies
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'Invalid graceid')

    @patch('src.api_v1.db')
    def test_post_event_galaxies_v1_missing_graceid(self, mock_db):
        models.db = mock_db
        response = self.client.post('/api/v1/event_galaxies', json={
            'api_token': 'valid_api_token',
            'timesent_stamp': self.valid_timesent_stamp,
            'galaxies': self.valid_galaxies
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'graceid is required')

    @patch('src.api_v1.db')
    def test_post_event_galaxies_v1_invalid_timesent_stamp(self, mock_db):
        models.db = mock_db
        mock_db.session.query(models.users).filter().first.return_value = MagicMock()
        mock_db.session.query().filter().all.return_value = [MagicMock()]
        response = self.client.post('/api/v1/event_galaxies', json={
            'api_token': 'valid_api_token',
            'graceid': 'valid_graceid',
            'timesent_stamp': 'not a timestamp',
            'galaxies': self.valid_galaxies
        })
        self.assertEqual(response.status_code, 500)
        self.assertIn('Error parsing date', response.data.decode())

    @patch('src.api_v1.db')
    def test_post_event_galaxies_v1_missing_timesent_stamp(self, mock_db):
        models.db = mock_db
        mock_db.session.query(models.users).filter().first.return_value = MagicMock()
        mock_db.session.query().filter().all.return_value = [MagicMock()]
        response = self.client.post('/api/v1/event_galaxies', json={
            'api_token': 'valid_api_token',
            'graceid': 'valid_graceid',
            'galaxies': self.valid_galaxies
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'timesent_stamp is required')

    @patch('src.api_v1.db')
    def test_post_event_galaxies_v1_missing_galaxies(self, mock_db):
        models.db = mock_db
        mock_db.session.query(models.users).filter().first.return_value = MagicMock()
        mock_db.session.query().filter().all.return_value = [MagicMock()]
        response = self.client.post('/api/v1/event_galaxies', json={
            'api_token': 'valid_api_token',
            'graceid': 'valid_graceid',
            'timesent_stamp': self.valid_timesent_stamp
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'a list of galaxies is required')

    @patch('src.api_v1.db')
    def test_add_pointings_v1_valid_request(self, mock_db):
        models.db = mock_db
        mock_db.session.query().filter().all.return_value = [MagicMock()] # mock for graceid
        mock_db.session.query(models.instrument.instrument_name, models.instrument.id).all.return_value = [instrument(id=1)]
        valid_pointings = [define_mock_pointing()]
        response = self.client.post('/api/v1/pointings', json={
            'api_token': 'valid_api_token',
            'graceid': 'valid_graceid',
            'pointings': valid_pointings
        })
        assert response.status_code == 200
        assert len(response.json['pointing_ids']) == len(valid_pointings)

    @patch('src.api_v1.db')
    def test_add_pointings_v1_invalid_grace_id(self, mock_db):
        models.db = mock_db
        mock_db.session.query().filter().all.side_effect = [[gw_alert(graceid='invalid', alternateid='invalid')], []] # mock for graceid
        response = self.client.post('/api/v1/pointings', json={
            'api_token': 'valid_api_token',
            'graceid': 'valid_graceid',
            'pointings': [define_mock_pointing()]
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'Invalid graceid')

    @patch('src.api_v1.db')
    def test_add_pointings_v1_missing_api_token(self, mock_db):
        valid_pointings = [define_mock_pointing()]
        response = self.client.post('/api/v1/pointings', json={
            'graceid': "valid_graceid",
            'pointings': valid_pointings
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(),'api_token is required')

    @patch('src.api_v1.db')
    def test_add_pointings_v1_invalid_api_token(self, mock_db):
        apitoken = 'invalid_api_token'
        mock_db.session.query(models.users).filter(models.users.api_token == 'invalid_api_token').first.return_value = None
        response = self.client.post('/api/v1/pointings', json={
            'api_token': apitoken,
            'graceid': 'valid_graceid',
            'pointings': define_mock_pointing()
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'Invalid api_token')

    @patch('src.api_v1.db')
    def test_add_pointings_v1_missing_graceid(self, mock_db):
        response = self.client.post('/api/v1/pointings', json={
            'api_token': 'valid_api_token',
            'pointings': define_mock_pointing()
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'graceid is required')

    @patch('src.api_v1.db')
    def test_add_pointings_v1_missing_pointings_format(self, mock_db):
        models.db = mock_db
        mock_db.session.query().filter().all.return_value = [MagicMock()] # mock for graceid
        response = self.client.post('/api/v1/pointings', json={
            'api_token': 'valid_api_token',
            'graceid': 'valid_graceid',
        })
        self.assertEqual(response.status_code, 500)
        self.assertTrue('Invalid request' in response.data.decode())

    @patch('src.api_v1.db')
    def test_get_pointings_v1_valid_request(self, mock_db):
        models.db = mock_db
        mock_db.session.query(models.users).filter().first.return_value = MagicMock()
        mock_db.session.query().filter().all.return_value = [MagicMock()]
        response = self.client.get('/api/v1/pointings', query_string={
            'api_token': 'valid_api_token',
            'graceid': 'valid_graceid'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

    @patch('src.api_v1.db')
    def test_get_pointings_v1_invalid_api_token(self, mock_db):
        mock_db.session.query(models.users).filter().first.return_value = None  # mock for invalid api_token
        response = self.client.get('/api/v1/pointings', query_string={
            'api_token': 'invalid_api_token',
            'graceid': 'valid_graceid'
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'Invalid api_token')

    @patch('src.api_v1.db')
    def test_get_pointings_v1_missing_api_token(self, mock_db):
        response = self.client.get('/api/v1/pointings', query_string={
            'graceid': 'valid_graceid'
        })
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'api_token is required')

    from unittest.mock import patch


    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db.session.query')
    def test_valid_request(self, mock_query, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'ra': '10.0', 'dec': '20.0'}, MagicMock())
        mock_query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        response = self.client.get('/api/v1/glade')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    @patch('src.api_v1.initial_request_parse')
    def test_invalid_request(self, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (False, 'Invalid request', None, None)

        response = self.client.get('/api/v1/glade')

        self.assertEqual(response.status_code, 500)
        self.assertIn('Invalid request', response.data.decode())

    @patch('src.api_v1.initial_request_parse')
    def test_initial_request_parsing_failure(self, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (False, 'Invalid Arguments.', None, None)

        response = self.client.get('/api/v1/glade')

        self.assertEqual(response.status_code, 500)
        self.assertIn('Invalid Arguments.', response.data.decode())

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db.session.query')
    def test_valid_ra_dec_parameters(self, mock_query, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'ra': '10.0', 'dec': '20.0'}, MagicMock())
        mock_query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        response = self.client.get('/api/v1/glade')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db.session.query')
    def test_filtering_by_name(self, mock_query, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'name': 'Andromeda'}, MagicMock())
        mock_query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        response = self.client.get('/api/v1/glade')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db.session.query')
    def test_filtering_and_ordering(self, mock_query, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'ra': '10.0', 'dec': '20.0', 'name': 'Andromeda'}, MagicMock())
        mock_query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        response = self.client.get('/api/v1/glade')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db.session.query')
    def test_successful_retrieval(self, mock_query, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {}, MagicMock())
        mock_query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        response = self.client.get('/api/v1/glade')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])


    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db')
    def test_query_alerts_success(self, mock_db, mock_initial_request_parse):
        models.db = mock_db
        # Mock the initial_request_parse to return valid data
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'S190425z'}, MagicMock())

        # Mock the database query
        mock_alert = MagicMock(
            parse={'graceid': 'S190425z', 'alert_type': 'Initial'})
        mock_db.session.query.filter.order_by.all.retrun_value = [mock_alert]

        response = self.client.get('/api/v1/query_alerts', query_string={'graceid': 'S190425z'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db')
    def test_query_alerts_invalid_request(self, mock_db, mock_initial_request_parse):
        models.db = mock_db
        # Mock the initial_request_parse to return invalid data
        mock_initial_request_parse.return_value = (False, 'Invalid request', {}, None)

        response = self.client.get('/api/v1/query_alerts')

        self.assertEqual(response.status_code, 500)
        self.assertIn('Invalid request', response.data.decode('utf-8'))

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db')
    def test_post_alert_success(self, mock_db, mock_initial_request_parse):
        # Mock the initial_request_parse to return valid data
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'S190425z'}, MagicMock(id=2))

        # Mock the database session
        mock_alert = MagicMock()
        mock_alert.parse = {'graceid': 'S190425z', 'alert_type': 'Initial'}
        mock_db.session.add.return_value = None
        mock_db.session.flush.return_value = None
        mock_db.session.commit.return_value = None

        response = self.client.post('/api/v1/post_alert', json={'graceid': 'S190425z'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('S190425z', response.data.decode('utf-8'))

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db')
    def test_post_alert_invalid_request(self, mock_db, mock_initial_request_parse):
        # Mock the initial_request_parse to return invalid data
        mock_initial_request_parse.return_value = (False, 'Invalid request', {}, None)

        response = self.client.post('/api/v1/post_alert')

        self.assertEqual(response.status_code, 500)
        self.assertIn('Invalid request', response.data.decode('utf-8'))

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db')
    def test_post_alert_unauthorized_user(self, mock_db, mock_initial_request_parse):
        # Mock the initial_request_parse to return a non-admin user
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'S190425z'}, MagicMock(id=1))

        response = self.client.post('/api/v1/post_alert', json={'graceid': 'S190425z'})

        self.assertEqual(response.status_code, 500)
        self.assertIn('Only admin can access this endpoint', response.data.decode('utf-8'))

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db')
    def test_get_grbmoc_v1_valid_request(self, mock_db, mock_initial_request_parse):
        models.db = mock_db
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'valid_graceid', 'instrument': 'gbm'}, MagicMock())
        mock_file = MagicMock()
        mock_file.read.return_value = b'file_content'
        mock_db.session.query().filter().all.return_value = [MagicMock()]
        with patch('src.api_v1.gwtm_io.download_gwtm_file', return_value=mock_file):
            response = self.client.get('/api/v1/grb_moc_file', query_string={'graceid': 'valid_graceid', 'instrument': 'gbm'})
            self.assertEqual(response.status_code, 200)

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db')
    def test_get_grbmoc_v1_invalid_graceid(self, mock_db, mock_initial_request_parse):
        models.db = mock_db
        mock_initial_request_parse.return_value = (True, '', {'instrument': 'gbm'}, MagicMock())
        response = self.client.get('/api/v1/grb_moc_file', query_string={'instrument': 'gbm'})
        self.assertEqual(response.status_code, 500)
        self.assertIn('graceid is required', response.data.decode())

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db')
    def test_get_grbmoc_v1_invalid_instrument(self, mock_db, mock_initial_request_parse):
        models.db = mock_db
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'valid_graceid'}, MagicMock())
        response = self.client.get('/api/v1/grb_moc_file', query_string={'graceid': 'valid_graceid'})
        self.assertEqual(response.status_code, 500)
        self.assertIn('Instrument is required', response.data.decode())

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db')
    def test_get_grbmoc_v1_invalid_instrument_value(self, mock_db, mock_initial_request_parse):
        models.db = mock_db
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'valid_graceid', 'instrument': 'invalid'}, MagicMock())
        response = self.client.get('/api/v1/grb_moc_file', query_string={'graceid': 'valid_graceid', 'instrument': 'invalid'})
        self.assertEqual(response.status_code, 500)
        self.assertIn('Valid instruments are in', response.data.decode())

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db')
    def test_get_grbmoc_v1_file_not_found(self, mock_db, mock_initial_request_parse):
        models.db = mock_db
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'valid_graceid', 'instrument': 'gbm'}, MagicMock())
        mock_db.session.query().filter().all.return_value = [MagicMock()]
        with patch('src.api_v1.gwtm_io.download_gwtm_file', side_effect=Exception('File not found')):
            response = self.client.get('/api/v1/grb_moc_file', query_string={'graceid': 'valid_graceid', 'instrument': 'gbm'})
            self.assertEqual(response.status_code, 200)
            self.assertIn('MOC file for GW-Alert', response.data.decode())

    @patch('src.api_v1.db')
    @patch('src.api_v1.initial_request_parse')
    def test_delete_single_valid_candidate(self, mock_initial_request_parse, mock_db):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_candidate = MagicMock()
        mock_candidate.submitterid = 1
        mock_candidate.id = 123

        mock_initial_request_parse.return_value = (True, '', {'id': 123}, mock_user)
        mock_db.session.query.return_value.filter.return_value.first.return_value = mock_candidate

        response = self.client.delete('/api/v1/candidate', json={'id': 123})

        self.assertEqual(response.status_code, 200)
        self.assertIn('Successfully deleted 1 candidate(s)', response.data.decode())

    @patch('src.api_v1.db')
    @patch('src.api_v1.initial_request_parse')
    def test_delete_invalid_candidate_id(self, mock_initial_request_parse, mock_db):
        mock_user = MagicMock()
        mock_user.id = 1

        mock_initial_request_parse.return_value = (True, '', {'id': 999}, mock_user)
        mock_db.session.query.return_value.filter.return_value.first.return_value = None

        response = self.client.delete('/api/v1/candidate', json={'id': 999})

        self.assertEqual(response.status_code, 500)
        self.assertIn('No candidate found with', response.data.decode())

    @patch('src.api_v1.db')
    @patch('src.api_v1.initial_request_parse')
    def test_delete_multiple_valid_candidates(self, mock_initial_request_parse, mock_db):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_candidate1 = MagicMock()
        mock_candidate1.submitterid = 1
        mock_candidate1.id = 123
        mock_candidate2 = MagicMock()
        mock_candidate2.submitterid = 1
        mock_candidate2.id = 124

        mock_initial_request_parse.return_value = (True, '', {'ids': [123, 124]}, mock_user)
        mock_db.session.query.return_value.filter.return_value.all.return_value = [mock_candidate1, mock_candidate2]

        response = self.client.delete('/api/v1/candidate', json={'ids': [123, 124]})

        self.assertEqual(response.status_code, 200)
        self.assertIn('Successfully deleted 2 candidate(s)', response.data.decode())

    @patch('src.api_v1.initial_request_parse')
    def test_delete_invalid_ids_format(self, mock_initial_request_parse):
        mock_user = MagicMock()
        mock_user.id = 1

        mock_initial_request_parse.return_value = (True, '', {'ids': 'invalid_format'}, mock_user)

        response = self.client.delete('/api/v1/candidate', json={'ids': 'invalid_format'})

        self.assertEqual(response.status_code, 500)
        self.assertIn('Invalid \'ids\' format', response.data.decode())

    @patch('src.api_v1.db')
    @patch('src.api_v1.initial_request_parse')
    def test_unauthorized_single_candidate_deletion(self, mock_initial_request_parse, mock_db):
        mock_user = MagicMock()
        mock_user.id = 2
        mock_candidate = MagicMock()
        mock_candidate.submitterid = 1
        mock_candidate.id = 123

        mock_initial_request_parse.return_value = (True, '', {'id': 123}, mock_user)
        mock_db.session.query.return_value.filter.return_value.first.return_value = mock_candidate

        response = self.client.delete('/api/v1/candidate', json={'id': 123})

        self.assertEqual(response.status_code, 500)
        self.assertIn('Error: Unauthorized', response.data.decode())


    @patch('src.api_v1.db')
    @patch('src.api_v1.initial_request_parse')
    def test_no_candidates_found_for_deletion(self, mock_initial_request_parse, mock_db):
        mock_user = MagicMock()
        mock_user.id = 1

        mock_initial_request_parse.return_value = (True, '', {'ids': [999, 1000]}, mock_user)
        mock_db.session.query.return_value.filter.return_value.all.return_value = []

        response = self.client.delete('/api/v1/candidate', json={'ids': [999, 1000]})

        self.assertEqual(response.status_code, 500)
        self.assertIn('No candidates found with input', response.data.decode())

    @patch('src.api_v1.initial_request_parse')
    def test_invalid_id_type(self, mock_initial_request_parse):
        mock_user = MagicMock()
        mock_user.id = 1

        mock_initial_request_parse.return_value = (True, '', {'id': 'invalid_type'}, mock_user)

        response = self.client.delete('/api/v1/candidate', json={'id': 'invalid_type'})

        self.assertEqual(response.status_code, 500)
        self.assertIn('Invalid candidate \'id\'', response.data.decode())

    @patch('src.api_v1.initial_request_parse')
    def test_invalid_ids_format_again(self, mock_initial_request_parse):
        mock_user = MagicMock()
        mock_user.id = 1

        mock_initial_request_parse.return_value = (True, '', {'ids': '[invalid]'}, mock_user)

        response = self.client.delete('/api/v1/candidate', json={'ids': '[invalid]'})

        self.assertEqual(response.status_code, 500)
        self.assertIn('Invalid \'ids\' format', response.data.decode())

    @patch('src.api_v1.db')
    @patch('src.api_v1.initial_request_parse')
    def test_successful_single_candidate_deletion(self, mock_initial_request_parse, mock_db):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_candidate = MagicMock()
        mock_candidate.submitterid = 1
        mock_candidate.id = 123

        mock_initial_request_parse.return_value = (True, '', {'id': 123}, mock_user)
        mock_db.session.query.return_value.filter.return_value.first.return_value = mock_candidate

        response = self.client.delete('/api/v1/candidate', json={'id': 123})

        self.assertEqual(response.status_code, 200)
        self.assertIn('Successfully deleted 1 candidate(s)', response.data.decode())

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.models.gw_alert.from_json')
    @patch('src.api_v1.db.session')
    def test_post_alert_v1_admin_user_success(self, mock_db_session, mock_from_json, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'alert_data': 'data'}, MagicMock(id=2))
        mock_from_json.return_value = MagicMock(parse={'alert': 'data'})
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        response = self.client.post('/api/v1/post_alert')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'alert': 'data'})

    @patch('src.api_v1.initial_request_parse')
    def test_post_alert_v1_non_admin_user(self, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {}, MagicMock(id=3))

        response = self.client.post('/api/v1/post_alert')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), "Only admin can access this endpoint")

    @patch('src.api_v1.initial_request_parse')
    def test_post_alert_v1_initial_request_parse_fail(self, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (False, 'Invalid request', None, None)

        response = self.client.post('/api/v1/post_alert')

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'Invalid request')


    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.models.gw_alert.from_json')
    @patch('src.api_v1.db.session')
    def test_post_alert_v1_successful_db_addition(self, mock_db_session, mock_from_json, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'alert_data': 'data'}, MagicMock(id=2))
        mock_from_json.return_value = MagicMock(parse={'alert': 'data'})
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        response = self.client.post('/api/v1/post_alert')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'alert': 'data'})



    @patch('src.api_v1.initial_request_parse')
    def test_initial_request_parse_fail(self, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (False, 'Invalid request', None, None)

        response = self.client.get('/api/v1/query_alerts')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'Invalid request')

    @patch('src.api_v1.initial_request_parse')
    def test_invalid_arguments_or_missing_api_token(self, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (False, 'api_token is required', None, None)

        response = self.client.get('/api/v1/query_alerts')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data.decode(), 'api_token is required')

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db.session.query')
    def test_graceid_filter(self, mock_query, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'G123'}, MagicMock())
        mock_alert = MagicMock()
        mock_alert.parse = {'id': 1, 'graceid': 'G123'}
        mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_alert]

        response = self.client.get('/api/v1/query_alerts')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db.session.query')
    def test_alert_type_filter(self, mock_query, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'alert_type': 'type1'}, MagicMock())
        mock_alert = MagicMock()
        mock_alert.parse = {'id': 1, 'alert_type': 'type1'}
        mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_alert]

        response = self.client.get('/api/v1/query_alerts')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db.session.query')
    def test_valid_filters_graceid_and_alert_type(self, mock_query, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'G123', 'alert_type': 'type1'}, MagicMock())
        mock_alert = MagicMock()
        mock_alert.parse = {'id': 1, 'graceid': 'G123', 'alert_type': 'type1'}
        mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_alert]

        response = self.client.get('/api/v1/query_alerts')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db.session.query')
    def test_alerts_parsed_to_json(self, mock_query, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'G123'}, MagicMock())
        mock_alert = MagicMock()
        mock_alert.parse = {'id': 1, 'graceid': 'G123'}
        mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_alert]

        response = self.client.get('/api/v1/query_alerts')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

    @patch('src.api_v1.initial_request_parse')
    @patch('src.api_v1.db.session.query')
    def test_successful_retrieval_with_valid_params(self, mock_query, mock_initial_request_parse):
        mock_initial_request_parse.return_value = (True, '', {'graceid': 'G123', 'alert_type': 'type1'}, MagicMock())
        mock_alert = MagicMock()
        mock_alert.parse = {'id': 1, 'graceid': 'G123', 'alert_type': 'type1'}
        mock_query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_alert]

        response = self.client.get('/api/v1/query_alerts')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.is_json, True)

if __name__ == '__main__':
    unittest.main()