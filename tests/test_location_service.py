
"""
Tests for Location Service
"""
import pytest
from unittest.mock import patch, Mock
from services.location_service import LocationService


class TestLocationService:
    """Test cases for LocationService"""
    
    def test_get_city_coordinates_valid_city(self):
        """Test getting coordinates for valid NZ city"""
        result = LocationService.get_city_coordinates('Auckland')
        
        assert result is not None
        assert 'lat' in result
        assert 'lng' in result
        assert result['lat'] == -36.8485
        assert result['lng'] == 174.7633
    
    def test_get_city_coordinates_invalid_city(self):
        """Test getting coordinates for invalid city"""
        result = LocationService.get_city_coordinates('InvalidCity')
        assert result is None
    
    def test_get_city_coordinates_case_sensitive(self):
        """Test that city names are case sensitive"""
        result = LocationService.get_city_coordinates('auckland')
        assert result is None
        
        result = LocationService.get_city_coordinates('Auckland')
        assert result is not None
    
    def test_validate_coordinates_valid(self):
        """Test coordinate validation with valid coordinates"""
        is_valid, errors = LocationService.validate_coordinates(-36.8485, 174.7633)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_coordinates_invalid_lat(self):
        """Test coordinate validation with invalid latitude"""
        is_valid, errors = LocationService.validate_coordinates(-91, 174.7633)
        
        assert is_valid is False
        assert len(errors) > 0
        assert 'latitude' in errors[0].lower()
    
    def test_validate_coordinates_invalid_lng(self):
        """Test coordinate validation with invalid longitude"""
        is_valid, errors = LocationService.validate_coordinates(-36.8485, 181)
        
        assert is_valid is False
        assert len(errors) > 0
        assert 'longitude' in errors[0].lower()
    
    def test_validate_coordinates_non_numeric(self):
        """Test coordinate validation with non-numeric values"""
        is_valid, errors = LocationService.validate_coordinates('invalid', 'invalid')
        
        assert is_valid is False
        assert len(errors) > 0
        assert 'valid numbers' in errors[0].lower()
    
    @patch('requests.get')
    def test_geocode_location_success(self, mock_get):
        """Test successful geocoding"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = [{
            'lat': '-36.8485',
            'lon': '174.7633',
            'display_name': 'Auckland, New Zealand',
            'address': {'city': 'Auckland', 'country': 'New Zealand'},
            'importance': 0.8
        }]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result, error = LocationService.geocode_location('Auckland')
        
        assert error is None
        assert result is not None
        assert result['lat'] == -36.8485
        assert result['lng'] == 174.7633
        assert 'Auckland' in result['display_name']
    
    @patch('requests.get')
    def test_geocode_location_no_results(self, mock_get):
        """Test geocoding with no results"""
        # Mock empty response
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result, error = LocationService.geocode_location('NonexistentPlace')
        
        assert result is None
        assert error is not None
        assert 'No results found' in error
    
    @patch('requests.get')
    def test_geocode_location_timeout(self, mock_get):
        """Test geocoding timeout handling"""
        # Mock timeout exception
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        result, error = LocationService.geocode_location('Auckland')
        
        assert result is None
        assert error is not None
        assert 'timed out' in error.lower()
    
    @patch('requests.get')
    def test_geocode_location_request_error(self, mock_get):
        """Test geocoding request error handling"""
        # Mock request exception
        import requests
        mock_get.side_effect = requests.exceptions.RequestException('Network error')
        
        result, error = LocationService.geocode_location('Auckland')
        
        assert result is None
        assert error is not None
        assert 'unavailable' in error.lower()
    
    def test_geocode_location_empty_query(self):
        """Test geocoding with empty query"""
        result, error = LocationService.geocode_location('')
        
        assert result is None
        assert error is not None
        assert 'empty' in error.lower()
    
    def test_geocode_location_none_query(self):
        """Test geocoding with None query"""
        result, error = LocationService.geocode_location(None)
        
        assert result is None
        assert error is not None
        assert 'empty' in error.lower()
    
    def test_format_location_for_storage_valid_data(self):
        """Test formatting valid location data"""
        input_data = {
            'lat': -36.8485,
            'lng': 174.7633,
            'display_name': 'Auckland, New Zealand',
            'address': {'city': 'Auckland'},
            'source': 'geocoding'
        }
        
        result = LocationService.format_location_for_storage(input_data)
        
        assert result['lat'] == -36.8485
        assert result['lng'] == 174.7633
        assert result['name'] == 'Auckland, New Zealand'
        assert result['source'] == 'geocoding'
    
    def test_format_location_for_storage_invalid_coordinates(self):
        """Test formatting with invalid coordinates"""
        input_data = {
            'lat': 'invalid',
            'lng': 'invalid',
            'display_name': 'Test Location'
        }
        
        with pytest.raises(ValueError):
            LocationService.format_location_for_storage(input_data)
    
    def test_get_location_summary(self):
        """Test generating location summary"""
        location_data = {
            'name': 'Auckland, New Zealand',
            'lat': -36.8485,
            'lng': 174.7633
        }
        
        summary = LocationService.get_location_summary(location_data)
        
        assert 'Auckland' in summary
        assert '-36.8485' in summary
        assert '174.7633' in summary
    
    def test_get_location_summary_minimal_data(self):
        """Test generating summary with minimal data"""
        location_data = {
            'lat': -36.8485,
            'lng': 174.7633
        }
        
        summary = LocationService.get_location_summary(location_data)
        
        assert 'Unknown Location' in summary or '-36.8485' in summary
    
    def test_nz_cities_data_integrity(self):
        """Test that all NZ cities have valid coordinates"""
        for city_name, coordinates in LocationService.NZ_CITIES.items():
            assert isinstance(city_name, str)
            assert len(city_name) > 0
            
            assert 'lat' in coordinates
            assert 'lng' in coordinates
            
            # Validate coordinates are in New Zealand range
            lat = coordinates['lat']
            lng = coordinates['lng']
            
            assert -47 <= lat <= -34  # New Zealand latitude range
            assert 166 <= lng <= 179  # New Zealand longitude range
