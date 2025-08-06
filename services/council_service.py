"""
Council Service - Handles council requirements and building code lookup
Refactored for better maintainability and performance
"""
import json
from typing import Dict, Any, Optional, List
from .base_service import CacheableService
from shapely.geometry import Polygon


class CouncilService(CacheableService):
    """Service for retrieving council-specific building requirements"""

    def __init__(self):
        super().__init__("CouncilService", cache_ttl=86400)  # 24 hour cache
        self.council_requirements = self._load_council_data()

    def _load_council_data(self) -> Dict[str, Any]:
        """Load council requirements data"""
        return {
            "Auckland Council": {
                "residential": {
                    "front_setback": 4.5,
                    "side_setback": 1.5,
                    "rear_setback": 3.0,
                    "max_height": 8.0,
                    "max_storeys": 2,
                    "site_coverage": 35,
                    "permeable_surface": 35,
                    "notes": "Single house zone requirements. Height in relation to boundary applies."
                },
                "mixed_housing_suburban": {
                    "front_setback": 4.5,
                    "side_setback": 1.0,
                    "rear_setback": 3.0,
                    "max_height": 8.0,
                    "max_storeys": 2,
                    "site_coverage": 40,
                    "permeable_surface": 30,
                    "notes": "Mixed Housing Suburban zone. Reduced side setbacks allowed."
                },
                "mixed_housing_urban": {
                    "front_setback": 3.0,
                    "side_setback": 1.0,
                    "rear_setback": 3.0,
                    "max_height": 11.0,
                    "max_storeys": 3,
                    "site_coverage": 50,
                    "permeable_surface": 20,
                    "notes": "Mixed Housing Urban zone. Higher density allowed."
                },
                "terraced_housing_apartment": {
                    "front_setback": 2.0,
                    "side_setback": 0.0,
                    "rear_setback": 3.0,
                    "max_height": 16.0,
                    "max_storeys": 4,
                    "site_coverage": 60,
                    "permeable_surface": 15,
                    "notes": "Terraced Housing and Apartment Buildings zone."
                }
            },
            "Wellington City Council": {
                "residential": {
                    "front_setback": 4.0,
                    "side_setback": 1.5,
                    "rear_setback": 3.0,
                    "max_height": 8.0,
                    "max_storeys": 2,
                    "site_coverage": 35,
                    "permeable_surface": 30,
                    "notes": "Outer Residential Area requirements."
                },
                "medium_density": {
                    "front_setback": 3.0,
                    "side_setback": 1.0,
                    "rear_setback": 3.0,
                    "max_height": 11.0,
                    "max_storeys": 3,
                    "site_coverage": 50,
                    "permeable_surface": 20,
                    "notes": "Medium Density Residential Area."
                }
            },
            "Christchurch City Council": {
                "residential": {
                    "front_setback": 4.5,
                    "side_setback": 1.5,
                    "rear_setback": 4.0,
                    "max_height": 8.0,
                    "max_storeys": 2,
                    "site_coverage": 35,
                    "permeable_surface": 25,
                    "notes": "Residential Suburban Zone requirements."
                },
                "medium_density": {
                    "front_setback": 3.0,
                    "side_setback": 1.0,
                    "rear_setback": 3.0,
                    "max_height": 11.0,
                    "max_storeys": 3,
                    "site_coverage": 45,
                    "permeable_surface": 20,
                    "notes": "Residential Medium Density Zone."
                }
            },
            "Hamilton City Council": {
                "residential": {
                    "front_setback": 4.5,
                    "side_setback": 1.5,
                    "rear_setback": 4.0,
                    "max_height": 8.0,
                    "max_storeys": 2,
                    "site_coverage": 40,
                    "permeable_surface": 30,
                    "notes": "Residential Zone requirements."
                }
            },
            "Tauranga City Council": {
                "residential": {
                    "front_setback": 6.0,
                    "side_setback": 1.5,
                    "rear_setback": 4.0,
                    "max_height": 8.0,
                    "max_storeys": 2,
                    "site_coverage": 35,
                    "permeable_surface": 30,
                    "notes": "General Residential Zone requirements."
                }
            },
            "Dunedin City Council": {
                "residential": {
                    "front_setback": 4.5,
                    "side_setback": 1.5,
                    "rear_setback": 4.0,
                    "max_height": 8.0,
                    "max_storeys": 2,
                    "site_coverage": 40,
                    "permeable_surface": 25,
                    "notes": "Residential Zone requirements."
                }
            }
        }

    def get_council_requirements(self, council_name: str, zoning: str = "residential") -> Optional[Dict[str, Any]]:
        """Get building requirements for a specific council and zone"""
        cache_key = f"{council_name}_{zoning}"
        cached_result = self._get_cache(cache_key)
        if cached_result:
            return cached_result

        try:
            council_key = self._normalize_council_name(council_name)

            if council_key not in self.council_requirements:
                self._log_operation("Council lookup", f"No requirements found for {council_name}")
                result = self._get_default_requirements()
                result['original_council'] = council_name
                self._set_cache(cache_key, result)
                return result

            council_data = self.council_requirements[council_key]
            zone_key = self._determine_zone_key(zoning, council_data)

            if zone_key in council_data:
                requirements = council_data[zone_key].copy()
                requirements.update({
                    'council': council_key,
                    'zone': zone_key,
                    'source': f"{council_key} District Plan"
                })

                self._log_operation("Requirements retrieved", f"{council_key} - {zone_key}")
                self._set_cache(cache_key, requirements)
                return requirements
            else:
                self.logger.warning(f"No zone data for {zone_key} in {council_key}")
                result = self._get_default_requirements()
                self._set_cache(cache_key, result)
                return result

        except Exception as e:
            return self._handle_error("get_council_requirements", e, self._get_default_requirements())

    def calculate_buildable_area(self, site_coords: List[List[float]], requirements: Dict[str, Any],
                               frontage: str = "auto", edge_classifications: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Calculate buildable area using geometry calculator"""
        try:
            print(f"[CouncilService] Buildable area calculation requested")
            print(f"[CouncilService] Site coords: {len(site_coords) if site_coords else 0} points")
            print(f"[CouncilService] Requirements: {requirements}")
            print(f"[CouncilService] Frontage: {frontage}")
            print(f"[CouncilService] Edge classifications: {len(edge_classifications) if edge_classifications else 0}")

            # Use the geometry calculator service
            from .geometry_calculator import GeometryCalculator

            calculator = GeometryCalculator()
            result = calculator.calculate_buildable_area(
                site_coords, requirements, frontage, edge_classifications
            )

            print(f"[CouncilService] Calculation result: {result}")

            self._log_operation("calculate_buildable_area", 
                              f"Calculated buildable area: {result.get('buildable_area_m2', 0):.1f} m²")

            return result

        except Exception as e:
            print(f"[CouncilService] ERROR in buildable area calculation: {str(e)}")
            return self._handle_error("calculate_buildable_area", e, {
                'buildable_coords': [],
                'buildable_area_m2': 0,
                'error': str(e),
                'calculation_method': 'error'
            })

    def _normalize_council_name(self, council_name: str) -> str:
        """Normalize council name to match database keys"""
        if not council_name or council_name.lower() in ['unknown', 'none', '']:
            self.logger.warning(f"Empty or unknown council name: '{council_name}', using default")
            return "Unknown Council"
            
        council_name = council_name.strip().lower()

        # Extended council mapping for better matching
        council_mapping = {
            'auckland': "Auckland Council",
            'wellington': "Wellington City Council", 
            'christchurch': "Christchurch City Council",
            'hamilton': "Hamilton City Council",
            'tauranga': "Tauranga City Council",
            'dunedin': "Dunedin City Council",
            'palmerston north': "Palmerston North City Council",
            'napier': "Napier City Council",
            'hastings': "Hastings District Council",
            'new plymouth': "New Plymouth District Council",
            'rotorua': "Rotorua Lakes District Council",
            'whangarei': "Whangarei District Council",
            'nelson': "Nelson City Council",
            'invercargill': "Invercargill City Council",
            'timaru': "Timaru District Council",
            'gisborne': "Gisborne District Council"
        }

        # Try exact and partial matches
        for key, value in council_mapping.items():
            if key in council_name or council_name in key:
                self.logger.info(f"Council mapped: '{council_name}' -> '{value}'")
                return value

        # Check exact matches against existing keys
        for key in self.council_requirements.keys():
            if council_name in key.lower() or key.lower() in council_name:
                self.logger.info(f"Council matched existing key: '{council_name}' -> '{key}'")
                return key

        # Try to extract city name from council string
        if 'council' in council_name:
            city_part = council_name.replace('council', '').replace('city', '').replace('district', '').strip()
            if city_part:
                for key, value in council_mapping.items():
                    if key == city_part or city_part in key:
                        self.logger.info(f"Council extracted and mapped: '{council_name}' -> '{value}'")
                        return value

        self.logger.warning(f"No specific data for '{council_name}', using default requirements")
        return "Unknown Council"

    def _determine_zone_key(self, zoning: str, council_data: Dict) -> str:
        """Determine the best matching zone key from available zones"""
        zoning_lower = zoning.lower()

        if zoning_lower in council_data:
            return zoning_lower

        # Pattern matching for common zone types
        if any(term in zoning_lower for term in ['mixed', 'medium', 'urban']):
            for zone in ['mixed_housing_urban', 'medium_density', 'mixed_housing_suburban']:
                if zone in council_data:
                    return zone

        if 'terraced' in zoning_lower or 'apartment' in zoning_lower:
            if 'terraced_housing_apartment' in council_data:
                return 'terraced_housing_apartment'

        return 'residential'

    def _get_default_requirements(self) -> Dict[str, Any]:
        """Return default NZ building requirements when specific council data unavailable"""
        return {
            "front_setback": 4.5,
            "side_setback": 1.5,
            "rear_setback": 3.5,
            "max_height": 8.0,
            "max_storeys": 2,
            "site_coverage": 35,
            "permeable_surface": 30,
            "council": "Industry Standard Estimation",
            "source": "NZ Building Code Industry Standards",
            "notes": "Industry standard estimation applied - specific council data not available."
        }


# Global service instance
council_service = CouncilService()