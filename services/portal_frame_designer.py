
import plotly.graph_objects as go
import numpy as np
from services.beam_service import BeamService

class PortalFrameDesigner:
    """Portal frame structure designer with parametric modeling capabilities"""
    
    def __init__(self):
        self.default_params = {
            'span': 20.0,
            'eave_height': 6.0,
            'ridge_height': 9.0,
            'portal_spacing': 6.0,
            'num_portals': 4,
            'beam_size': (0.3, 0.6),
            'column_size': (0.3, 0.6),
            'purlin_size': (0.1, 0.1),
            'girt_size': (0.1, 0.1),
            'bracing_size': (0.08, 0.08),
            'girt_spacing': 1.5,
            'purlin_spacing': 1.5,
            'end_column_y_offset': 3.0,
            'add_end_columns': True
        }
    
    def generate_portal_frame(self, parameters):
        """Generate a portal frame structure based on input parameters"""
        try:
            # Merge with defaults
            params = {**self.default_params, **parameters}
            
            # Get beam selections if session_id is provided
            session_id = parameters.get('session_id')
            beam_selections = {}
            if session_id:
                beam_selections = BeamService.get_user_beam_selections(session_id)
            
            # Apply beam selections to parameters
            if 'column' in beam_selections:
                column_spec = BeamService.convert_beam_spec_to_frame_params(beam_selections['column'])
                params.update({
                    'column_depth': column_spec['depth'],
                    'column_width': column_spec['width'],
                    'column_flange_thickness': column_spec['flange_thickness'],
                    'column_web_thickness': column_spec['web_thickness']
                })
                # Update column_size tuple
                params['column_size'] = (column_spec['width'], column_spec['depth'])
            
            if 'beam' in beam_selections:
                beam_spec = BeamService.convert_beam_spec_to_frame_params(beam_selections['beam'])
                params.update({
                    'beam_depth': beam_spec['depth'],
                    'beam_width': beam_spec['width'],
                    'beam_flange_thickness': beam_spec['flange_thickness'],
                    'beam_web_thickness': beam_spec['web_thickness']
                })
                # Update beam_size tuple
                params['beam_size'] = (beam_spec['width'], beam_spec['depth'])
            
            # Create plotly figure using the enhanced portal structure code
            portal_data = self.create_enhanced_portal_structure(**params)
            
            # Create plotly figure
            fig = go.Figure()
            
            # Add individual member meshes
            individual_members = portal_data['individual_members']
            members = portal_data['members']
            
            for member_data in individual_members:
                vertices = member_data['vertices']
                faces = member_data['faces']
                metadata = member_data['metadata']
                element_type = member_data['element_type']
                
                if len(vertices) > 0 and len(faces) > 0:
                    x, y, z = zip(*vertices)
                    i, j, k = zip(*faces)
                    
                    # Color code by member type
                    color_map = {
                        'column': 'steelblue',
                        'beam': 'lightcoral',
                        'rafter_beam': 'lightgreen'
                    }
                    color = color_map.get(element_type, 'steelblue')
                    
                    fig.add_trace(go.Mesh3d(
                        x=x, y=y, z=z,
                        i=i, j=j, k=k,
                        color=color,
                        opacity=0.9,
                        name=metadata['designation'],
                        showscale=False,
                        customdata=[metadata['id']],  # Store member ID for selection
                        hovertemplate=f"<b>{metadata['designation']}</b><br>" +
                                    f"Type: {metadata['type']}<br>" +
                                    f"Length: {metadata['length']:.2f}m<br>" +
                                    f"Cross Section: {metadata['cross_section']}<extra></extra>"
                    ))
            
            # No reference plane - slab will be auto-generated separately if needed
            
            # Add axis lines
            max_dimension = max(
                params['num_portals'] * params['portal_spacing'],
                params['span'],
                params['ridge_height']
            )
            axis_traces = self.create_axis_lines(length=max_dimension)
            for trace in axis_traces:
                fig.add_trace(trace)
            
            # Configure layout
            fig.update_layout(
                scene=dict(
                    xaxis_title='X (m)',
                    yaxis_title='Y (m)',
                    zaxis_title='Z (m)',
                    aspectmode='data'
                ),
                title='Portal Frame Structure',
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            # Calculate statistics from member metadata
            member_counts = {}
            for member in members:
                member_type = member['type']
                member_counts[member_type] = member_counts.get(member_type, 0) + 1
            
            total_columns = member_counts.get('column', 0)
            total_beams = member_counts.get('beam', 0)
            total_rafter_beams = member_counts.get('rafter_beam', 0)
            
            stats = {
                'total_columns': total_columns,
                'total_beams': total_beams,
                'total_rafter_beams': total_rafter_beams,
                'total_members': len(members),
                'member_breakdown': member_counts,
                'num_portals': params['num_portals'],
                'span': params['span'],
                'ridge_height': params['ridge_height'],
                'eave_height': params['eave_height'],
                'portal_spacing': params['portal_spacing']
            }
            
            # Ensure the parameters include the structural system type
            params['structural_system_type'] = 'portal_frame'
            
            return {
                'success': True,
                'figure': fig,
                'stats': stats,
                'parameters': params,
                'members': members
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_enhanced_portal_structure(self, span=20, eave_height=6, ridge_height=9, 
                                       portal_spacing=6, num_portals=4, beam_size=(0.3, 0.6), 
                                       column_size=(0.3, 0.6), purlin_size=(0.1, 0.1), 
                                       girt_size=(0.1, 0.1), bracing_size=(0.08, 0.08),
                                       girt_spacing=1.5, purlin_spacing=1.5, 
                                       end_column_y_offset=3.0, add_end_columns=True, **kwargs):
        """Create enhanced portal structure with individual member meshes"""
        individual_members = []  # Store individual member meshes
        all_members = []  # Track members with metadata

        beam_w, beam_d = beam_size
        col_w, col_d = column_size
        pur_w, pur_d = purlin_size
        girt_w, girt_d = girt_size
        br_w, br_d = bracing_size

        portal_x = [i * portal_spacing for i in range(num_portals)]

        # --- Portal Columns and Rafters (as I-Beams) ---
        for portal_idx, x in enumerate(portal_x):
            # Columns (left and right) - positioned from 0 to span
            for col_idx, y in enumerate([0, span]):
                start = [x, y, 0]
                end = [x, y, eave_height]
                v, f = self.generate_i_beam_mesh(start, end, col_w, col_d)
                if v:
                    # Calculate orientation and assign metadata
                    orientation = self.calculate_member_orientation(start, end)
                    member_type = self.classify_member_type(start, end, orientation)
                    
                    member_metadata = {
                        'id': f'portal_{portal_idx}_column_{col_idx}',
                        'type': member_type,
                        'orientation': orientation,
                        'start_point': start,
                        'end_point': end,
                        'length': np.linalg.norm(np.array(end) - np.array(start)),
                        'cross_section': 'i-beam',
                        'dimensions': {'width': col_w, 'depth': col_d},
                        'designation': f'Column {portal_idx+1}-{col_idx+1}'
                    }
                    all_members.append(member_metadata)
                    
                    # Create individual member mesh
                    individual_members.append({
                        'vertices': v,
                        'faces': f,
                        'metadata': member_metadata,
                        'element_type': member_type
                    })

            # Rafters - ridge at center of span
            ridge = [x, span/2, ridge_height]
            for rafter_idx, y in enumerate([0, span]):
                start = [x, y, eave_height]
                end = ridge
                v, f = self.generate_i_beam_mesh(start, end, beam_w, beam_d)
                if v:
                    # Calculate orientation and assign metadata
                    orientation = self.calculate_member_orientation(start, end)
                    member_type = self.classify_member_type(start, end, orientation)
                    
                    member_metadata = {
                        'id': f'portal_{portal_idx}_rafter_{rafter_idx}',
                        'type': member_type,
                        'orientation': orientation,
                        'start_point': start,
                        'end_point': end,
                        'length': np.linalg.norm(np.array(end) - np.array(start)),
                        'cross_section': 'i-beam',
                        'dimensions': {'width': beam_w, 'depth': beam_d},
                        'designation': f'Rafter {portal_idx+1}-{rafter_idx+1}'
                    }
                    all_members.append(member_metadata)
                    
                    # Create individual member mesh
                    individual_members.append({
                        'vertices': v,
                        'faces': f,
                        'metadata': member_metadata,
                        'element_type': member_type
                    })

        # --- Roof Purlins (rectangular), spaced by purlin_spacing ---
        # Position purlins on top of rafters (rafter beam depth / 2)
        purlin_offset_z = beam_d / 2
        half_span = span / 2
        rafter_length = np.linalg.norm([0, half_span, ridge_height - eave_height])
        num_purlins = int(rafter_length // purlin_spacing)

        for i in range(num_portals - 1):
            x0 = portal_x[i]
            x1 = portal_x[i + 1]
            for j in range(num_purlins):
                # Calculate position along rafter length
                distance_along_rafter = (j + 1) * purlin_spacing
                frac = distance_along_rafter / rafter_length
                
                # For each side of the roof (left and right rafter)
                for side in ['left', 'right']:
                    if side == 'left':
                        # Left rafter goes from (0, eave_height) to (span/2, ridge_height)
                        y = frac * half_span
                        z = eave_height + frac * (ridge_height - eave_height)
                    else:
                        # Right rafter goes from (span, eave_height) to (span/2, ridge_height)
                        y = span - frac * half_span
                        z = eave_height + frac * (ridge_height - eave_height)
                    
                    # Position purlins on top of rafter beams
                    z += purlin_offset_z
                    
                    p0 = [x0, y, z]
                    p1 = [x1, y, z]
                    v, f = self.generate_beam_mesh(p0, p1, pur_w, pur_d)
                    if v:
                        # Create purlin metadata
                        orientation = self.calculate_member_orientation(p0, p1)
                        member_type = self.classify_member_type(p0, p1, orientation)
                        
                        purlin_metadata = {
                            'id': f'purlin_{i}_{j}_{side}',
                            'type': 'beam',
                            'orientation': orientation,
                            'start_point': p0,
                            'end_point': p1,
                            'length': np.linalg.norm(np.array(p1) - np.array(p0)),
                            'cross_section': 'rectangular',
                            'dimensions': {'width': pur_w, 'depth': pur_d},
                            'designation': f'Purlin {i+1}-{j+1}-{side}'
                        }
                        all_members.append(purlin_metadata)
                        
                        # Create individual member mesh
                        individual_members.append({
                            'vertices': v,
                            'faces': f,
                            'metadata': purlin_metadata,
                            'element_type': 'beam'
                        })

        # --- Wall Girts (rectangular), spaced by girt_spacing ---
        num_girts = int(eave_height // girt_spacing)
        for i in range(num_portals - 1):
            x0 = portal_x[i]
            x1 = portal_x[i + 1]
            for g in range(1, num_girts + 1):
                h = g * girt_spacing
                for y_side in [0, span]:
                    # Adjust girt position based on column depth
                    if y_side == 0:
                        # Girts closest to origin: reduce y by column depth / 2
                        y_adjusted = y_side - col_d / 2
                    else:
                        # Girts furthest from origin: increase y by column depth / 2  
                        y_adjusted = y_side + col_d / 2
                        
                    p0 = [x0, y_adjusted, h]
                    p1 = [x1, y_adjusted, h]
                    v, f = self.generate_beam_mesh(p0, p1, girt_w, girt_d)
                    if v:
                        # Create girt metadata
                        orientation = self.calculate_member_orientation(p0, p1)
                        member_type = self.classify_member_type(p0, p1, orientation)
                        
                        girt_metadata = {
                            'id': f'girt_{i}_{g}_{y_side}',
                            'type': 'beam',
                            'orientation': orientation,
                            'start_point': p0,
                            'end_point': p1,
                            'length': np.linalg.norm(np.array(p1) - np.array(p0)),
                            'cross_section': 'rectangular',
                            'dimensions': {'width': girt_w, 'depth': girt_d},
                            'designation': f'Girt {i+1}-{g}-{y_side}'
                        }
                        all_members.append(girt_metadata)
                        
                        # Create individual member mesh
                        individual_members.append({
                            'vertices': v,
                            'faces': f,
                            'metadata': girt_metadata,
                            'element_type': 'beam'
                        })

        # --- End Columns (if enabled) ---
        if add_end_columns:
            for end_idx, x in enumerate([portal_x[0], portal_x[-1]]):
                for offset_idx, y_offset_dir in enumerate([-1, 1]):
                    y = span/2 + y_offset_dir * end_column_y_offset
                    # Ensure y is within bounds
                    y = max(0, min(span, y))
                    # Linear interpolation of height under pitched beam
                    dist_from_center = abs(y - span/2)
                    frac = 1 - dist_from_center / (span / 2)
                    height = eave_height + (ridge_height - eave_height) * frac
                    start = [x, y, 0]
                    end = [x, y, height]
                    v, f = self.generate_i_beam_mesh(start, end, col_w, col_d)
                    if v:
                        # Create end column metadata
                        orientation = self.calculate_member_orientation(start, end)
                        member_type = self.classify_member_type(start, end, orientation)
                        
                        end_col_metadata = {
                            'id': f'end_column_{end_idx}_{offset_idx}',
                            'type': member_type,
                            'orientation': orientation,
                            'start_point': start,
                            'end_point': end,
                            'length': np.linalg.norm(np.array(end) - np.array(start)),
                            'cross_section': 'i-beam',
                            'dimensions': {'width': col_w, 'depth': col_d},
                            'designation': f'End Column {end_idx+1}-{offset_idx+1}'
                        }
                        all_members.append(end_col_metadata)
                        
                        # Create individual member mesh
                        individual_members.append({
                            'vertices': v,
                            'faces': f,
                            'metadata': end_col_metadata,
                            'element_type': member_type
                        })
        
        return {
            'individual_members': individual_members,
            'members': all_members
        }
    
    def calculate_member_orientation(self, start, end):
        """Calculate the orientation angles of a structural member"""
        start = np.array(start)
        end = np.array(end)
        direction = end - start
        
        if np.linalg.norm(direction) == 0:
            return {'horizontal_angle': 0, 'vertical_angle': 0}
        
        direction = direction / np.linalg.norm(direction)
        
        # Calculate horizontal angle (in XY plane)
        horizontal_projection = np.array([direction[0], direction[1], 0])
        if np.linalg.norm(horizontal_projection) > 0:
            horizontal_projection = horizontal_projection / np.linalg.norm(horizontal_projection)
            # Angle from X-axis
            horizontal_angle = np.degrees(np.arctan2(horizontal_projection[1], horizontal_projection[0]))
        else:
            horizontal_angle = 0
        
        # Calculate vertical angle (elevation from horizontal)
        horizontal_length = np.sqrt(direction[0]**2 + direction[1]**2)
        if horizontal_length > 0:
            vertical_angle = np.degrees(np.arctan2(direction[2], horizontal_length))
        else:
            vertical_angle = 90 if direction[2] > 0 else -90
        
        return {
            'horizontal_angle': horizontal_angle,
            'vertical_angle': vertical_angle
        }
    
    def classify_member_type(self, start, end, orientation):
        """Classify structural member type based on orientation"""
        vertical_angle = orientation['vertical_angle']
        
        # Define thresholds for classification
        VERTICAL_THRESHOLD = 75  # degrees from horizontal
        HORIZONTAL_THRESHOLD = 15  # degrees from horizontal
        
        if abs(vertical_angle) >= VERTICAL_THRESHOLD:
            return 'column'
        elif abs(vertical_angle) <= HORIZONTAL_THRESHOLD:
            return 'beam'
        else:
            # Angled member above horizontal
            if vertical_angle > HORIZONTAL_THRESHOLD:
                return 'rafter_beam'
            else:
                return 'beam'  # Slightly angled beam
    
    def generate_beam_mesh(self, start, end, width, depth):
        """Creates a simple rectangular beam (solid prism) between start and end."""
        start = np.array(start)
        end = np.array(end)
        axis = end - start
        length = np.linalg.norm(axis)
        if length == 0:
            return [], []

        axis /= length
        up = np.array([0, 0, 1]) if abs(np.dot(axis, [0, 0, 1])) < 0.9 else np.array([0, 1, 0])
        side = np.cross(axis, up)
        side /= np.linalg.norm(side)
        up = np.cross(side, axis)

        hw, hd = width / 2, depth / 2

        corners = [
            -side * hw - up * hd,
            side * hw - up * hd,
            side * hw + up * hd,
            -side * hw + up * hd,
        ]

        vertices = []
        for i in [0, 1]:
            offset = start + axis * length * i
            for c in corners:
                vertices.append(offset + c)

        faces = [
            [0, 1, 2], [0, 2, 3],  # bottom
            [4, 5, 6], [4, 6, 7],  # top
            [0, 1, 5], [0, 5, 4],
            [1, 2, 6], [1, 6, 5],
            [2, 3, 7], [2, 7, 6],
            [3, 0, 4], [3, 4, 7]
        ]

        return vertices, faces
    
    def generate_i_beam_mesh(self, start, end, width, depth, flange_thickness_ratio=0.15, web_thickness_ratio=0.25):
        """Generate I-beam mesh geometry"""
        start = np.array(start)
        end = np.array(end)
        direction = end - start
        length = np.linalg.norm(direction)
        
        if length == 0 or length < 1e-10:
            return [], []

        direction = direction / length
        up_guess = np.array([0, 0, 1]) if not np.allclose(direction, [0, 0, 1]) else np.array([0, 1, 0])
        side = np.cross(direction, up_guess)
        side_norm = np.linalg.norm(side)
        
        if side_norm < 1e-10:
            up_guess = np.array([1, 0, 0])
            side = np.cross(direction, up_guess)
            side_norm = np.linalg.norm(side)
        
        if side_norm < 1e-10:
            return [], []
            
        side = side / side_norm
        up = np.cross(side, direction)
        up_norm = np.linalg.norm(up)
        
        if up_norm < 1e-10:
            return [], []
            
        up = up / up_norm

        flange_thickness = depth * flange_thickness_ratio
        web_thickness = width * web_thickness_ratio

        # Create I-beam profile points
        profile = [
            [-width/2, -depth/2],
            [width/2, -depth/2],
            [width/2, -depth/2 + flange_thickness],
            [web_thickness/2, -depth/2 + flange_thickness],
            [web_thickness/2, depth/2 - flange_thickness],
            [width/2, depth/2 - flange_thickness],
            [width/2, depth/2],
            [-width/2, depth/2],
            [-width/2, depth/2 - flange_thickness],
            [-web_thickness/2, depth/2 - flange_thickness],
            [-web_thickness/2, -depth/2 + flange_thickness],
            [-width/2, -depth/2 + flange_thickness]
        ]

        vertices = []
        for frac in [0, 1]:
            origin = start + frac * length * direction
            for x, y in profile:
                point = origin + x * side + y * up
                vertices.append(point)

        num_pts = len(profile)
        faces = []
        for n in range(num_pts):
            n_next = (n + 1) % num_pts
            faces.extend([
                [n, n_next, n_next + num_pts],
                [n, n_next + num_pts, n + num_pts]
            ])

        return vertices, faces

    def create_xy_plane(self, x_range, y_range, z=0):
        """Create a base XY plane"""
        x0, x1 = x_range
        y0, y1 = y_range
        vertices = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
        x, y, z = zip(*vertices)
        return go.Mesh3d(
            x=x + (x[0],), y=y + (y[0],), z=z + (z[0],),
            i=[0, 0], j=[1, 2], k=[2, 3],
            color='gray', opacity=0.1,
            name='XY Plane', showscale=False
        )

    def create_slab_mesh(self, x_range, y_range, thickness=0.3):
        """Create a 3D slab mesh with proper thickness"""
        x0, x1 = x_range
        y0, y1 = y_range
        
        # Create vertices for the top and bottom faces of the slab
        # Bottom face (z=0)
        bottom_vertices = [
            (x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)
        ]
        # Top face (z=thickness)
        top_vertices = [
            (x0, y0, thickness), (x1, y0, thickness), (x1, y1, thickness), (x0, y1, thickness)
        ]
        
        # Combine all vertices
        all_vertices = bottom_vertices + top_vertices
        x, y, z = zip(*all_vertices)
        
        # Define faces using vertex indices
        # Bottom face: 0,1,2,3
        # Top face: 4,5,6,7
        faces = [
            # Bottom face (2 triangles)
            [0, 1, 2], [0, 2, 3],
            # Top face (2 triangles)
            [4, 5, 6], [4, 6, 7],
            # Side faces (4 sides, 2 triangles each)
            # Front side
            [0, 1, 5], [0, 5, 4],
            # Right side
            [1, 2, 6], [1, 6, 5],
            # Back side
            [2, 3, 7], [2, 7, 6],
            # Left side
            [3, 0, 4], [3, 4, 7]
        ]
        
        i, j, k = zip(*faces)
        
        return go.Mesh3d(
            x=x, y=y, z=z,
            i=i, j=j, k=k,
            color='lightgray',
            opacity=0.8,
            name=f'Concrete Slab ({thickness}m thick)',
            showscale=False
        )

    def create_axis_lines(self, length=10):
        """Create axis lines"""
        return [
            go.Scatter3d(x=[0, length], y=[0, 0], z=[0, 0], mode='lines',
                         line=dict(color='red', width=6), name='X Axis'),
            go.Scatter3d(x=[0, 0], y=[0, length], z=[0, 0], mode='lines',
                         line=dict(color='green', width=6), name='Y Axis'),
            go.Scatter3d(x=[0, 0], y=[0, 0], z=[0, length], mode='lines',
                         line=dict(color='blue', width=6), name='Z Axis')
        ]
