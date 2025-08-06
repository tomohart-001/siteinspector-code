"""
The code has been updated with a method to get the beam designation by element type.
"""
"""
Beam Service - Manages I-beam specifications and selections
"""
import sqlite3
from typing import List, Dict, Any, Optional
from database import db_manager
from utils.logger import app_logger


class BeamService:
    """Service for managing I-beam specifications and selections"""

    @staticmethod
    def _ensure_beam_tables_exist():
        """Ensure beam specification tables exist"""
        try:
            with db_manager.db.get_cursor() as cursor:
                # I-beam specifications table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS beam_specifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        material TEXT NOT NULL,
                        designation TEXT NOT NULL,
                        section_depth_mm REAL NOT NULL,
                        grade_mpa REAL NOT NULL,
                        density_kg_m REAL NOT NULL,
                        width_mm REAL NOT NULL,
                        flange_thickness_mm REAL NOT NULL,
                        web_thickness_mm REAL NOT NULL,
                        section_area_mm2 REAL NOT NULL,
                        moment_inertia_x_mm4 REAL NOT NULL,
                        section_modulus_x_mm3 REAL NOT NULL,
                        moment_inertia_y_mm4 REAL NOT NULL,
                        section_modulus_y_mm3 REAL NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(material, designation, grade_mpa)
                    )
                ''')

                # User beam selections table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_beam_selections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        element_type TEXT NOT NULL,
                        beam_specification_id INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (beam_specification_id) REFERENCES beam_specifications (id)
                    )
                ''')

                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_beam_specs_material ON beam_specifications(material)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_beam_specs_designation ON beam_specifications(designation)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_selections_session ON user_beam_selections(session_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_selections_element ON user_beam_selections(element_type)')

            app_logger.info("Beam specification tables initialized successfully")
        except Exception as e:
            app_logger.error(f"Failed to initialize beam tables: {e}")
            raise

    @staticmethod
    def get_all_beam_specifications() -> List[Dict[str, Any]]:
        """Get all beam specifications with complete metadata"""
        BeamService._ensure_beam_tables_exist()

        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT id, material, designation, section_depth_mm, grade_mpa,
                           density_kg_m, width_mm, flange_thickness_mm, web_thickness_mm,
                           section_area_mm2, moment_inertia_x_mm4, section_modulus_x_mm3,
                           moment_inertia_y_mm4, section_modulus_y_mm3, created_at
                    FROM beam_specifications
                    ORDER BY material, designation, grade_mpa
                ''')

                specifications = [dict(row) for row in cursor.fetchall()]
                app_logger.info(f"Retrieved {len(specifications)} beam specifications with complete metadata")
                return specifications
        except Exception as e:
            app_logger.error(f"Failed to get beam specifications: {e}")
            return []

    @staticmethod
    def get_beam_specification(spec_id: int) -> Optional[Dict[str, Any]]:
        """Get specific beam specification by ID"""
        BeamService._ensure_beam_tables_exist()

        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT id, material, designation, section_depth_mm, grade_mpa,
                           density_kg_m, width_mm, flange_thickness_mm, web_thickness_mm,
                           section_area_mm2, moment_inertia_x_mm4, section_modulus_x_mm3,
                           moment_inertia_y_mm4, section_modulus_y_mm3
                    FROM beam_specifications
                    WHERE id = ?
                ''', (spec_id,))

                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            app_logger.error(f"Failed to get beam specification {spec_id}: {e}")
            return None

    @staticmethod
    def get_beam_specification_by_designation(designation: str) -> Optional[Dict[str, Any]]:
        """Get specific beam specification by designation"""
        BeamService._ensure_beam_tables_exist()

        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT id, material, designation, section_depth_mm, grade_mpa,
                           density_kg_m, width_mm, flange_thickness_mm, web_thickness_mm,
                           section_area_mm2, moment_inertia_x_mm4, section_modulus_x_mm3,
                           moment_inertia_y_mm4, section_modulus_y_mm3
                    FROM beam_specifications
                    WHERE designation = ?
                    ORDER BY grade_mpa DESC
                    LIMIT 1
                ''', (designation,))

                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            app_logger.error(f"Failed to get beam specification by designation {designation}: {e}")
            return None

    @staticmethod
    def add_beam_specification(spec_data: Dict[str, Any]) -> int:
        """Add new beam specification"""
        BeamService._ensure_beam_tables_exist()

        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO beam_specifications (
                        material, designation, section_depth_mm, grade_mpa,
                        density_kg_m, width_mm, flange_thickness_mm, web_thickness_mm,
                        section_area_mm2, moment_inertia_x_mm4, section_modulus_x_mm3,
                        moment_inertia_y_mm4, section_modulus_y_mm3
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    spec_data['material'],
                    spec_data['designation'],
                    spec_data['section_depth_mm'],
                    spec_data['grade_mpa'],
                    spec_data['density_kg_m'],
                    spec_data['width_mm'],
                    spec_data['flange_thickness_mm'],
                    spec_data['web_thickness_mm'],
                    spec_data['section_area_mm2'],
                    spec_data['moment_inertia_x_mm4'],
                    spec_data['section_modulus_x_mm3'],
                    spec_data['moment_inertia_y_mm4'],
                    spec_data['section_modulus_y_mm3']
                ))

                spec_id = cursor.lastrowid
                app_logger.info(f"Added beam specification: {spec_data['designation']} ({spec_id})")
                return spec_id
        except Exception as e:
            app_logger.error(f"Failed to add beam specification: {e}")
            raise

    @staticmethod
    def save_user_beam_selection(session_id: str, element_type: str, beam_spec_id: int) -> bool:
        """Save user's beam selection for a specific element type"""
        BeamService._ensure_beam_tables_exist()

        try:
            with db_manager.db.get_cursor() as cursor:
                # Remove existing selection for this element type
                cursor.execute('''
                    DELETE FROM user_beam_selections 
                    WHERE session_id = ? AND element_type = ?
                ''', (session_id, element_type))

                # Add new selection
                cursor.execute('''
                    INSERT INTO user_beam_selections (session_id, element_type, beam_specification_id)
                    VALUES (?, ?, ?)
                ''', (session_id, element_type, beam_spec_id))

                app_logger.info(f"Saved beam selection for {element_type}: {beam_spec_id}")
                return True
        except Exception as e:
            app_logger.error(f"Failed to save beam selection: {e}")
            return False

    @staticmethod
    def get_user_beam_selections(session_id: str) -> Dict[str, Dict[str, Any]]:
        """Get user's beam selections for all element types"""
        BeamService._ensure_beam_tables_exist()

        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT ubs.element_type, bs.*
                    FROM user_beam_selections ubs
                    JOIN beam_specifications bs ON ubs.beam_specification_id = bs.id
                    WHERE ubs.session_id = ?
                ''', (session_id,))

                selections = {}
                for row in cursor.fetchall():
                    element_type = row['element_type']
                    selections[element_type] = dict(row)

                return selections
        except Exception as e:
            app_logger.error(f"Failed to get user beam selections: {e}")
            return {}

    @staticmethod
    def get_beam_specifications_metadata() -> Dict[str, Any]:
        """Get metadata about beam specifications for change detection"""
        BeamService._ensure_beam_tables_exist()

        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT COUNT(*) as count, 
                           MAX(created_at) as last_modified,
                           GROUP_CONCAT(designation ORDER BY designation) as designations
                    FROM beam_specifications
                ''')

                row = cursor.fetchone()
                if row:
                    return {
                        'count': row['count'],
                        'last_modified': row['last_modified'],
                        'designations_hash': hash(row['designations']) if row['designations'] else 0
                    }
                else:
                    return {'count': 0, 'last_modified': None, 'designations_hash': 0}
        except Exception as e:
            app_logger.error(f"Failed to get beam specifications metadata: {e}")
            return {'count': 0, 'last_modified': None, 'designations_hash': 0}

    @staticmethod
    def convert_beam_spec_to_frame_params(beam_spec: Dict[str, Any]) -> Dict[str, float]:
        """Convert beam specification to rigid frame parameters (mm to m)"""
        return {
            'depth': beam_spec['section_depth_mm'] / 1000.0,  # mm to m
            'width': beam_spec['width_mm'] / 1000.0,  # mm to m
            'flange_thickness': beam_spec['flange_thickness_mm'] / 1000.0,  # mm to m
            'web_thickness': beam_spec['web_thickness_mm'] / 1000.0,  # mm to m
            'density': beam_spec['density_kg_m'],  # Already in kg/m
            'section_area': beam_spec['section_area_mm2'] / 1000000.0,  # mm² to m²
            'moment_inertia_x': beam_spec['moment_inertia_x_mm4'] / 1000000000000.0,  # mm⁴ to m⁴
            'section_modulus_x': beam_spec['section_modulus_x_mm3'] / 1000000000.0,  # mm³ to m³
            'moment_inertia_y': beam_spec['moment_inertia_y_mm4'] / 1000000000000.0,  # mm⁴ to m⁴
            'section_modulus_y': beam_spec['section_modulus_y_mm3'] / 1000000000.0,  # mm³ to m³
        }

    @staticmethod
    def initialize_default_beam_specifications():
        """Initialize database with common Australian/NZ steel beam specifications"""
        BeamService._ensure_beam_tables_exist()

        # Common steel beam specifications
        default_specs = [
            {
                'material': 'Steel',
                'designation': '610UB125',
                'section_depth_mm': 612,
                'grade_mpa': 250,
                'density_kg_m': 7850,  # Steel density, not section weight
                'width_mm': 229,
                'flange_thickness_mm': 19.6,
                'web_thickness_mm': 11.9,
                'section_area_mm2': 15900,
                'moment_inertia_x_mm4': 985000000,
                'section_modulus_x_mm3': 3220000,
                'moment_inertia_y_mm4': 39300000,
                'section_modulus_y_mm3': 343000
            },
            {
                'material': 'Steel',
                'designation': '760UB173',
                'section_depth_mm': 770,
                'grade_mpa': 250,
                'density_kg_m': 7850,  # Steel density, not section weight
                'width_mm': 267,
                'flange_thickness_mm': 21.6,
                'web_thickness_mm': 14.3,
                'section_area_mm2': 22000,
                'moment_inertia_x_mm4': 2050000000,
                'section_modulus_x_mm3': 5390000,
                'moment_inertia_y_mm4': 687000000,
                'section_modulus_y_mm3': 515000
            },
            {
                'material': 'Steel',
                'designation': '310UB32',
                'section_depth_mm': 308,
                'grade_mpa': 300,
                'density_kg_m': 7850,  # Steel density, not section weight
                'width_mm': 101,
                'flange_thickness_mm': 10.2,
                'web_thickness_mm': 6.1,
                'section_area_mm2': 4070,
                'moment_inertia_x_mm4': 108000000,
                'section_modulus_x_mm3': 701000,
                'moment_inertia_y_mm4': 3640000,
                'section_modulus_y_mm3': 72100
            },
            {
                'material': 'Steel',
                'designation': '460UB82',
                'section_depth_mm': 460,
                'grade_mpa': 300,
                'density_kg_m': 7850,  # Steel density, not section weight
                'width_mm': 191,
                'flange_thickness_mm': 16.0,
                'web_thickness_mm': 9.9,
                'section_area_mm2': 10500,
                'moment_inertia_x_mm4': 554000000,
                'section_modulus_x_mm3': 2410000,
                'moment_inertia_y_mm4': 35500000,
                'section_modulus_y_mm3': 372000
            }
        ]

        try:
            existing_specs = BeamService.get_all_beam_specifications()
            if not existing_specs:
                for spec in default_specs:
                    BeamService.add_beam_specification(spec)
                app_logger.info(f"Initialized {len(default_specs)} default beam specifications")
            else:
                app_logger.info(f"Beam specifications already exist ({len(existing_specs)} found)")
        except Exception as e:
            app_logger.error(f"Failed to initialize default beam specifications: {e}")

    @staticmethod
    def get_beam_designation_by_type(session_id: str, element_type: str) -> Optional[str]:
        """Get beam designation for a specific element type and session"""
        BeamService._ensure_beam_tables_exist()

        try:
            with db_manager.db.get_cursor() as cursor:
                cursor.execute('''
                    SELECT bs.designation
                    FROM user_beam_selections ubs
                    JOIN beam_specifications bs ON ubs.beam_specification_id = bs.id
                    WHERE ubs.session_id = ? AND ubs.element_type = ?
                ''', (session_id, element_type))

                result = cursor.fetchone()
                return result[0] if result else None

        except Exception as e:
            app_logger.error(f"Error getting beam designation for {element_type}: {e}")
            return None


# Create service instance
beam_service = BeamService()