"""
Floor Plan Processing Service
Handles floor plan upload, processing, and boundary detection with improved accuracy
"""
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import base64
import io
from typing import Dict, Any, List, Tuple, Optional
from .base_service import BaseService


class FloorplanService(BaseService):
    """Service for processing floor plan images and extracting boundaries with improved accuracy"""

    def __init__(self):
        super().__init__("FloorplanService")
        # Streamlined configuration
        self.config = {
            'area_ratio_min': 0.01,
            'area_ratio_max': 0.85,
            'min_solidity': 0.2,
            'polygon_epsilon': 0.008,
            'morphology_kernel': 3,
            'gaussian_blur': 3,
            'adaptive_block': 15,
            'adaptive_c': 8,
            'canny_lower': 30,
            'canny_upper': 100,
        }

    def _ensure_json_serializable(self, data):
        """Convert numpy types to JSON serializable types"""
        if isinstance(data, np.integer):
            return int(data)
        elif isinstance(data, np.floating):
            return float(data)
        elif isinstance(data, np.ndarray):
            return data.tolist()
        elif isinstance(data, dict):
            return {key: self._ensure_json_serializable(value) for key, value in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._ensure_json_serializable(item) for item in data]
        else:
            return data

    def process_floorplan_image(self, image_data: str, scale_reference: Optional[float] = None) -> Dict[str, Any]:
        """Process uploaded floor plan image and extract boundary coordinates"""
        try:
            self._log_operation("Floor plan processing started")

            # Decode and preprocess image
            image = self._decode_base64_image(image_data)
            preprocessed = self._preprocess_image(image)

            # Extract boundaries
            boundaries = self._extract_boundaries(preprocessed, image.shape)
            boundaries = self._validate_boundaries(boundaries, image.shape)

            # Convert to coordinates and calculate metrics
            coordinates = self._boundaries_to_coordinates(boundaries, scale_reference)
            metrics = self._calculate_metrics(boundaries, coordinates)

            result = {
                'success': True,
                'boundaries': boundaries,
                'coordinates': coordinates,
                'metrics': metrics,
                'processed_image': self._encode_processed_image(image, boundaries),
                'processing_method': 'enhanced_cv'
            }

            result = self._ensure_json_serializable(result)
            self._log_operation("Floor plan processing completed", f"Found {len(boundaries)} boundary points")

            return result

        except Exception as e:
            return self._handle_error("Floor plan processing", e, {
                'success': False,
                'error': str(e),
                'boundaries': [],
                'coordinates': []
            })

    def _decode_base64_image(self, image_data: str) -> np.ndarray:
        """Decode base64 image data to numpy array"""
        try:
            # Remove data URL prefix if present
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]

            # Decode and load image
            image_bytes = base64.b64decode(image_data)
            pil_image = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB
            if pil_image.mode not in ['RGB', 'L']:
                pil_image = pil_image.convert('RGB')
            elif pil_image.mode == 'L':
                pil_image = pil_image.convert('RGB')

            # Convert to OpenCV format
            image_array = np.array(pil_image)

            if len(image_array.shape) == 3:
                return cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
            else:
                return cv2.cvtColor(image_array, cv2.COLOR_GRAY2BGR)

        except Exception as e:
            raise ValueError(f"Failed to decode image: {str(e)}")

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for boundary detection"""
        try:
            # Convert to grayscale
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()

            # Normalize and enhance contrast
            normalized = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

            # Apply CLAHE for local contrast enhancement
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(normalized)

            return enhanced

        except Exception as e:
            self.logger.warning(f"Preprocessing failed, using basic processing: {e}")
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    def _extract_boundaries(self, image: np.ndarray, original_shape: tuple) -> List[Tuple[int, int]]:
        """Extract boundary points using multiple detection methods"""
        height, width = image.shape[:2]
        image_area = height * width

        # Try multiple detection methods
        methods = [
            self._method_adaptive_threshold,
            self._method_canny_contours,
            self._method_architectural_detection
        ]

        for method in methods:
            try:
                boundaries = method(image, image_area)
                if boundaries and len(boundaries) >= 4:
                    self.logger.info(f"Successful detection with {method.__name__}: {len(boundaries)} points")
                    return boundaries
            except Exception as e:
                self.logger.debug(f"{method.__name__} failed: {e}")
                continue

        # Fallback boundaries
        self.logger.warning("All methods failed, using fallback boundaries")
        return self._generate_fallback_boundaries(width, height)

    def _method_adaptive_threshold(self, image: np.ndarray, image_area: int) -> Optional[List[Tuple[int, int]]]:
        """Method 1: Adaptive thresholding approach"""
        # Apply adaptive threshold
        thresh = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, self.config['adaptive_block'], self.config['adaptive_c']
        )

        # Morphological operations
        kernel = np.ones((self.config['morphology_kernel'], self.config['morphology_kernel']), np.uint8)
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel)

        # Find and process contours
        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return self._process_contours(contours, image_area)

    def _method_canny_contours(self, image: np.ndarray, image_area: int) -> Optional[List[Tuple[int, int]]]:
        """Method 2: Canny edge detection approach"""
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(image, (self.config['gaussian_blur'], self.config['gaussian_blur']), 0)

        # Canny edge detection
        edges = cv2.Canny(blurred, self.config['canny_lower'], self.config['canny_upper'])

        # Morphological closing to connect edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return self._process_contours(contours, image_area)

    def _method_architectural_detection(self, image: np.ndarray, image_area: int) -> Optional[List[Tuple[int, int]]]:
        """Method 3: Architectural outline detection"""
        # Multiple threshold levels
        _, thresh1 = cv2.threshold(image, 200, 255, cv2.THRESH_BINARY_INV)
        _, thresh2 = cv2.threshold(image, 150, 255, cv2.THRESH_BINARY_INV)
        _, thresh3 = cv2.threshold(image, 100, 255, cv2.THRESH_BINARY_INV)

        # Combine thresholds
        combined = cv2.bitwise_or(thresh1, cv2.bitwise_or(thresh2, thresh3))

        # Remove small details and close gaps
        kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opened = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_open)

        kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel_close)

        # Find contours
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return self._process_contours(contours, image_area)

    def _process_contours(self, contours: List, image_area: int) -> Optional[List[Tuple[int, int]]]:
        """Process contours to find the best boundary"""
        if not contours:
            return None

        valid_contours = []

        for contour in contours:
            area = cv2.contourArea(contour)

            # Area filter
            if area < image_area * self.config['area_ratio_min'] or area > image_area * self.config['area_ratio_max']:
                continue

            # Solidity filter
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                solidity = area / hull_area
                if solidity < self.config['min_solidity']:
                    continue

            # Aspect ratio filter
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else float('inf')
            if aspect_ratio > 10:
                continue

            valid_contours.append((contour, area))

        if not valid_contours:
            return None

        # Select largest valid contour
        best_contour = max(valid_contours, key=lambda x: x[1])[0]

        # Approximate to polygon
        epsilon = self.config['polygon_epsilon'] * cv2.arcLength(best_contour, True)
        approx = cv2.approxPolyDP(best_contour, epsilon, True)

        # Extract boundary points
        boundaries = [(int(point[0][0]), int(point[0][1])) for point in approx]

        # Ensure reasonable number of points
        if len(boundaries) < 4:
            step = max(1, len(best_contour) // 8)
            boundaries = [(int(point[0][0]), int(point[0][1])) for point in best_contour[::step]]

        if len(boundaries) > 20:
            step = len(boundaries) // 15
            boundaries = boundaries[::step]

        return boundaries

    def _validate_boundaries(self, boundaries: List[Tuple[int, int]], image_shape: tuple) -> List[Tuple[int, int]]:
        """Validate and clean up extracted boundaries"""
        if not boundaries or len(boundaries) < 3:
            height, width = image_shape[:2]
            return self._generate_fallback_boundaries(width, height)

        # Remove duplicate points
        unique_boundaries = []
        for point in boundaries:
            if not unique_boundaries or self._point_distance(point, unique_boundaries[-1]) > 5:
                unique_boundaries.append(point)

        return unique_boundaries

    def _point_distance(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Calculate distance between two points"""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    def _generate_fallback_boundaries(self, width: int, height: int) -> List[Tuple[int, int]]:
        """Generate reasonable fallback boundaries"""
        margin_x = width // 8
        margin_y = height // 8

        return [
            (margin_x, margin_y),
            (width - margin_x, margin_y),
            (width - margin_x, height - margin_y),
            (margin_x, height - margin_y)
        ]

    def _boundaries_to_coordinates(self, boundaries: List[Tuple[int, int]], 
                                 scale_reference: Optional[float] = None) -> List[Dict[str, float]]:
        """Convert image pixel boundaries to relative coordinates"""
        if not boundaries:
            return []

        # Get bounds and normalize
        min_x = min(point[0] for point in boundaries)
        max_x = max(point[0] for point in boundaries)
        min_y = min(point[1] for point in boundaries)
        max_y = max(point[1] for point in boundaries)

        width = max_x - min_x
        height = max_y - min_y

        normalized_coords = []
        for x, y in boundaries:
            norm_x = (x - min_x) / width if width > 0 else 0
            norm_y = (y - min_y) / height if height > 0 else 0
            normalized_coords.append({'x': norm_x, 'y': norm_y})

        return normalized_coords

    def _calculate_metrics(self, boundaries: List[Tuple[int, int]], 
                         coordinates: List[Dict[str, float]]) -> Dict[str, Any]:
        """Calculate metrics for the floor plan"""
        try:
            if len(boundaries) < 3:
                return {'area': 0, 'perimeter': 0, 'boundary_points': 0}

            # Calculate area using Shoelace formula
            area = 0
            n = len(coordinates)
            for i in range(n):
                j = (i + 1) % n
                area += coordinates[i]['x'] * coordinates[j]['y']
                area -= coordinates[j]['x'] * coordinates[i]['y']
            area = abs(area) / 2

            # Calculate perimeter
            perimeter = 0
            for i in range(len(boundaries)):
                j = (i + 1) % len(boundaries)
                dx = boundaries[j][0] - boundaries[i][0]
                dy = boundaries[j][1] - boundaries[i][1]
                perimeter += np.sqrt(dx*dx + dy*dy)

            # Calculate compactness
            compactness = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0

            return {
                'area': float(area),
                'perimeter': float(perimeter),
                'boundary_points': len(boundaries),
                'complexity_score': len(boundaries) / 4,
                'compactness': float(compactness),
                'processing_quality': 'high' if compactness > 0.3 else 'medium' if compactness > 0.1 else 'low'
            }

        except Exception as e:
            self.logger.warning(f"Failed to calculate metrics: {e}")
            return {'area': 0, 'perimeter': 0, 'boundary_points': len(boundaries)}

    def _encode_processed_image(self, image: np.ndarray, boundaries: List[Tuple[int, int]]) -> str:
        """Encode processed image with highlighted boundaries as base64"""
        try:
            processed = image.copy()

            if len(boundaries) > 2:
                points = np.array(boundaries, np.int32)
                points = points.reshape((-1, 1, 2))

                # Draw outline and fill
                cv2.polylines(processed, [points], True, (0, 255, 0), 4)

                for point in boundaries:
                    cv2.circle(processed, point, 6, (255, 0, 0), -1)
                    cv2.circle(processed, point, 6, (255, 255, 255), 2)

                overlay = processed.copy()
                cv2.fillPoly(overlay, [points], (0, 255, 0))
                processed = cv2.addWeighted(processed, 0.85, overlay, 0.15, 0)

            # Convert and encode
            processed_rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(processed_rgb)

            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')

            return f"data:image/png;base64,{encoded}"

        except Exception as e:
            self.logger.warning(f"Failed to encode processed image: {e}")
            return ""

    def scale_floorplan_to_buildable_area(self, floorplan_coords: List[Dict[str, float]], 
                                        buildable_coords: List[Dict[str, float]], 
                                        scale_factor: float = 0.8) -> List[Dict[str, float]]:
        """Scale and position floor plan within the buildable area"""
        try:
            self.logger.info(f"Scaling floor plan: {len(floorplan_coords) if floorplan_coords else 0} to {len(buildable_coords) if buildable_coords else 0} coords")

            if not floorplan_coords or not buildable_coords:
                self.logger.error("Missing coordinates for scaling")
                return []

            # Handle different coordinate formats
            if isinstance(buildable_coords[0], dict):
                buildable_lats = [coord['lat'] for coord in buildable_coords]
                buildable_lngs = [coord['lng'] for coord in buildable_coords]
            else:
                buildable_lats = [coord[0] for coord in buildable_coords]
                buildable_lngs = [coord[1] for coord in buildable_coords]

            # Calculate bounds and center
            min_lat, max_lat = min(buildable_lats), max(buildable_lats)
            min_lng, max_lng = min(buildable_lngs), max(buildable_lngs)

            center_lat = (min_lat + max_lat) / 2
            center_lng = (min_lng + max_lng) / 2

            buildable_width = max_lng - min_lng
            buildable_height = max_lat - min_lat

            # Scale coordinates
            scaled_coords = []
            for coord in floorplan_coords:
                scaled_x = (coord['x'] - 0.5) * buildable_width * scale_factor
                scaled_y = (coord['y'] - 0.5) * buildable_height * scale_factor

                scaled_coords.append({
                    'lat': center_lat + scaled_y,
                    'lng': center_lng + scaled_x
                })

            self._log_operation("Floor plan scaled to buildable area", f"Scale factor: {scale_factor}, Points: {len(scaled_coords)}")
            return scaled_coords

        except Exception as e:
            return self._handle_error("Floor plan scaling", e, [])

    def convert_to_geojson_polygon(self, coordinates: List[Dict[str, float]], 
                                 center_lat: float, center_lng: float, 
                                 scale_meters: float = None) -> Dict[str, Any]:
        """Convert normalized coordinates to GeoJSON polygon"""
        try:
            if not coordinates:
                return None

            # Auto-scale if not provided
            if scale_meters is None:
                min_x = min(coord['x'] for coord in coordinates)
                max_x = max(coord['x'] for coord in coordinates)
                min_y = min(coord['y'] for coord in coordinates)
                max_y = max(coord['y'] for coord in coordinates)

                norm_area = (max_x - min_x) * (max_y - min_y)
                scale_meters = max(20, min(80, 20 + (norm_area * 200)))

                self.logger.info(f"Auto-calculated scale: {scale_meters}m (norm_area: {norm_area:.4f})")

            # Convert to GeoJSON coordinates
            geojson_coords = []
            for coord in coordinates:
                offset_x = (coord['x'] - 0.5) * scale_meters
                offset_y = (coord['y'] - 0.5) * scale_meters

                lat_offset = offset_y / 111320
                lng_offset = offset_x / (111320 * np.cos(np.radians(center_lat)))

                lng = center_lng + lng_offset
                lat = center_lat + lat_offset
                geojson_coords.append([lng, lat])

            # Close polygon
            if geojson_coords[0] != geojson_coords[-1]:
                geojson_coords.append(geojson_coords[0])

            geojson_polygon = {
                "type": "Feature",
                "properties": {
                    "type": "floorplan",
                    "scale_meters": scale_meters,
                    "rotation": 0,
                    "locked": False
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [geojson_coords]
                }
            }

            self._log_operation("Converted to GeoJSON polygon", f"Points: {len(geojson_coords)}, Scale: {scale_meters}m")
            return geojson_polygon

        except Exception as e:
            return self._handle_error("GeoJSON conversion", e, None)


# Global instance
floorplan_service = FloorplanService()