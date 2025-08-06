
import plotly.graph_objects as go
import numpy as np
from services.beam_service import BeamService

class RigidFrameDesigner:
    """Rigid frame structure designer with parametric modeling capabilities"""
    
    def __init__(self):
        self.default_params = {
            'building_length': 20.0,
            'building_width': 10.0,
            'bay_spacing_x': 5.0,
            'bay_spacing_y': 5.0,
            'column_depth': 0.3,
            'column_width': 0.2,
            'column_flange_thickness': 0.015,
            'column_web_thickness': 0.01,
            'beam_depth': 0.4,
            'beam_width': 0.15,
            'beam_flange_thickness': 0.015,
            'beam_web_thickness': 0.01,
            'column_height': 4.0
        }
    
    def generate_rigid_frame(self, parameters):
        """Generate a rigid frame structure based on input parameters"""
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
            
            if 'beam' in beam_selections:
                beam_spec = BeamService.convert_beam_spec_to_frame_params(beam_selections['beam'])
                params.update({
                    'beam_depth': beam_spec['depth'],
                    'beam_width': beam_spec['width'],
                    'beam_flange_thickness': beam_spec['flange_thickness'],
                    'beam_web_thickness': beam_spec['web_thickness']
                })
            
            # Calculate derived parameters
            num_bays_x = max(1, int(params['building_length'] / params['bay_spacing_x']))
            num_bays_y = max(1, int(params['building_width'] / params['bay_spacing_y']))
            num_storeys = params.get('num_storeys', 1)
            storey_height = params.get('storey_height', params['column_height'])
            
            actual_length = num_bays_x * params['bay_spacing_x']
            actual_width = num_bays_y * params['bay_spacing_y']
            total_height = num_storeys * storey_height
            
            # Generate column positions
            column_positions = []
            for i in range(num_bays_x + 1):
                for j in range(num_bays_y + 1):
                    x = i * params['bay_spacing_x']
                    y = j * params['bay_spacing_y']
                    column_positions.append((x, y, 0))
            
            # Create plotly figure
            fig = go.Figure()
            
            # Add columns (height reduced by beam depth / 2)
            reduced_height = total_height - (params['beam_depth'] / 2)
            for pos in column_positions:
                x, y, z, i_indices, j_indices, k_indices = self.generate_i_beam_mesh(
                    start=[pos[0], pos[1], pos[2]],
                    end=[pos[0], pos[1], pos[2] + reduced_height],
                    width=params['column_width'],
                    depth=params['column_depth'],
                    flange_thickness_ratio=params['column_flange_thickness'] / params['column_depth'],
                    web_thickness_ratio=params['column_web_thickness'] / params['column_width']
                )
                
                if x:  # Only add if mesh generation was successful
                    fig.add_trace(go.Mesh3d(
                        x=x, y=y, z=z,
                        i=i_indices, j=j_indices, k=k_indices,
                        color='steelblue',
                        opacity=0.9,
                        name='column',
                        showscale=False
                    ))
            
            # Add beams for each storey
            for storey in range(num_storeys):
                beam_height = (storey + 1) * storey_height
                
                # Add beams (X direction) for this storey - shortened by beam width to properly intersect columns
                for j in range(num_bays_y + 1):
                    for i in range(num_bays_x):
                        # X-direction beams (shortened by beam width)
                        x0 = i * params['bay_spacing_x'] + params['beam_width'] / 2
                        x1 = (i + 1) * params['bay_spacing_x'] - params['beam_width'] / 2
                        
                        start_pos = [x0, j * params['bay_spacing_y'], beam_height]
                        end_pos = [x1, j * params['bay_spacing_y'], beam_height]
                        
                        x, y, z, i_indices, j_indices, k_indices = self.generate_i_beam_mesh(
                            start=start_pos,
                            end=end_pos,
                            width=params['beam_width'],
                            depth=params['beam_depth'],
                            flange_thickness_ratio=params['beam_flange_thickness'] / params['beam_depth'],
                            web_thickness_ratio=params['beam_web_thickness'] / params['beam_width']
                        )
                        
                        if x:  # Only add if mesh generation was successful
                            fig.add_trace(go.Mesh3d(
                                x=x, y=y, z=z,
                                i=i_indices, j=j_indices, k=k_indices,
                                color='orange',
                                opacity=0.9,
                                name='beam',
                                showscale=False
                            ))
                
                # Add beams (Y direction) for this storey
                for i in range(num_bays_x + 1):
                    for j in range(num_bays_y):
                        if storey == num_storeys - 1:  # Top level
                            # Y-direction beams (reduce starting position by column width/2, increase length by column width/2)
                            if j == 0:
                                y0 = j * params['bay_spacing_y'] - params['column_width'] / 2
                                y1 = (j + 1) * params['bay_spacing_y']
                            elif j == num_bays_y - 1:  # Last bay
                                y0 = j * params['bay_spacing_y']
                                y1 = (j + 1) * params['bay_spacing_y'] + params['column_width'] / 2   
                            else:
                                y0 = j * params['bay_spacing_y']
                                y1 = (j + 1) * params['bay_spacing_y']

                        else:  # All other levels
                            # Y-direction beams (reduce length by column width/2 at each end)
                            y0 = j * params['bay_spacing_y'] + params['column_width'] / 2
                            y1 = (j + 1) * params['bay_spacing_y'] - params['column_width'] / 2
                        
                        start_pos = [i * params['bay_spacing_x'], y0, beam_height]
                        end_pos = [i * params['bay_spacing_x'], y1, beam_height]
                        
                        x, y, z, i_indices, j_indices, k_indices = self.generate_i_beam_mesh(
                            start=start_pos,
                            end=end_pos,
                            width=params['beam_width'],
                            depth=params['beam_depth'],
                            flange_thickness_ratio=params['beam_flange_thickness'] / params['beam_depth'],
                            web_thickness_ratio=params['beam_web_thickness'] / params['beam_width']
                        )
                        
                        if x:  # Only add if mesh generation was successful
                            fig.add_trace(go.Mesh3d(
                                x=x, y=y, z=z,
                                i=i_indices, j=j_indices, k=k_indices,
                                color='orange',
                                opacity=0.9,
                                name='beam',
                                showscale=False
                            ))
            
            # Add XY plane
            plane_trace = self.create_xy_plane(
                x_range=(0, actual_length),
                y_range=(0, actual_width),
                z=0
            )
            fig.add_trace(plane_trace)
            
            # Add axis lines
            axis_traces = self.create_axis_lines(length=max(actual_length, actual_width, total_height))
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
                title='Rigid Frame Structure',
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            # Generate member metadata
            members = []
            member_id = 0
            
            # Add column metadata
            for i, pos in enumerate(column_positions):
                for storey in range(num_storeys):
                    member_id += 1
                    start_point = [pos[0], pos[1], storey * storey_height]
                    end_point = [pos[0], pos[1], (storey + 1) * storey_height - (params['beam_depth'] / 2)]
                    
                    members.append({
                        'id': f'column_{member_id}',
                        'type': 'column',
                        'designation': f'Column {member_id}',
                        'cross_section': 'I-beam',
                        'length': end_point[2] - start_point[2],
                        'orientation': {
                            'horizontal_angle': 0,
                            'vertical_angle': 90
                        },
                        'dimensions': {
                            'width': params['column_width'],
                            'depth': params['column_depth']
                        },
                        'start_point': start_point,
                        'end_point': end_point
                    })
            
            # Add beam metadata
            for storey in range(num_storeys):
                beam_height = (storey + 1) * storey_height
                
                # X-direction beams
                for j in range(num_bays_y + 1):
                    for i in range(num_bays_x):
                        member_id += 1
                        start_point = [i * params['bay_spacing_x'] + params['beam_width'] / 2, 
                                     j * params['bay_spacing_y'], beam_height]
                        end_point = [(i + 1) * params['bay_spacing_x'] - params['beam_width'] / 2,
                                   j * params['bay_spacing_y'], beam_height]
                        
                        members.append({
                            'id': f'beam_{member_id}',
                            'type': 'beam',
                            'designation': f'Beam {member_id}',
                            'cross_section': 'I-beam',
                            'length': end_point[0] - start_point[0],
                            'orientation': {
                                'horizontal_angle': 0,
                                'vertical_angle': 0
                            },
                            'dimensions': {
                                'width': params['beam_width'],
                                'depth': params['beam_depth']
                            },
                            'start_point': start_point,
                            'end_point': end_point
                        })
                
                # Y-direction beams
                for i in range(num_bays_x + 1):
                    for j in range(num_bays_y):
                        member_id += 1
                        if storey == num_storeys - 1:  # Top level
                            if j == 0:
                                y0 = j * params['bay_spacing_y'] - params['column_width'] / 2
                                y1 = (j + 1) * params['bay_spacing_y']
                            elif j == num_bays_y - 1:
                                y0 = j * params['bay_spacing_y']
                                y1 = (j + 1) * params['bay_spacing_y'] + params['column_width'] / 2
                            else:
                                y0 = j * params['bay_spacing_y']
                                y1 = (j + 1) * params['bay_spacing_y']
                        else:
                            y0 = j * params['bay_spacing_y'] + params['column_width'] / 2
                            y1 = (j + 1) * params['bay_spacing_y'] - params['column_width'] / 2
                        
                        start_point = [i * params['bay_spacing_x'], y0, beam_height]
                        end_point = [i * params['bay_spacing_x'], y1, beam_height]
                        
                        members.append({
                            'id': f'beam_{member_id}',
                            'type': 'beam',
                            'designation': f'Beam {member_id}',
                            'cross_section': 'I-beam',
                            'length': abs(y1 - y0),
                            'orientation': {
                                'horizontal_angle': 90,
                                'vertical_angle': 0
                            },
                            'dimensions': {
                                'width': params['beam_width'],
                                'depth': params['beam_depth']
                            },
                            'start_point': start_point,
                            'end_point': end_point
                        })
            
            # Calculate statistics
            total_columns = len(column_positions) * num_storeys
            beams_per_storey = num_bays_x * (num_bays_y + 1) + num_bays_y * (num_bays_x + 1)
            total_beams = beams_per_storey * num_storeys
            
            stats = {
                'total_columns': total_columns,
                'total_beams': total_beams,
                'num_bays_x': num_bays_x,
                'num_bays_y': num_bays_y,
                'num_storeys': num_storeys,
                'storey_height': storey_height,
                'total_height': total_height,
                'actual_length': actual_length,
                'actual_width': actual_width
            }
            
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
    
    def generate_i_beam_mesh(self, start, end, width, depth, flange_thickness_ratio=0.15, web_thickness_ratio=0.25):
        """Generate I-beam mesh geometry"""
        start = np.array(start)
        end = np.array(end)
        direction = end - start
        length = np.linalg.norm(direction)
        
        if length == 0 or length < 1e-10:
            return [], [], [], [], [], []

        direction = direction / length
        up_guess = np.array([0, 0, 1]) if not np.allclose(direction, [0, 0, 1]) else np.array([0, 1, 0])
        side = np.cross(direction, up_guess)
        side_norm = np.linalg.norm(side)
        
        # Handle case where direction is parallel to up_guess
        if side_norm < 1e-10:
            up_guess = np.array([1, 0, 0])
            side = np.cross(direction, up_guess)
            side_norm = np.linalg.norm(side)
        
        if side_norm < 1e-10:
            return [], [], [], [], [], []
            
        side = side / side_norm
        up = np.cross(side, direction)
        up_norm = np.linalg.norm(up)
        
        if up_norm < 1e-10:
            return [], [], [], [], [], []
            
        up = up / up_norm

        flange_thickness = depth * flange_thickness_ratio
        web_thickness = width * web_thickness_ratio

        # Create I-beam profile points in counter-clockwise order
        # Start from bottom-left of bottom flange
        profile = [
            # Bottom flange (left to right)
            [-width/2, -depth/2],                           # Bottom-left corner
            [width/2, -depth/2],                            # Bottom-right corner
            [width/2, -depth/2 + flange_thickness],         # Bottom-right flange top
            [web_thickness/2, -depth/2 + flange_thickness], # Right web bottom
            # Right side of web (bottom to top)
            [web_thickness/2, depth/2 - flange_thickness],  # Right web top
            [width/2, depth/2 - flange_thickness],          # Top-right flange bottom
            # Top flange (right to left)
            [width/2, depth/2],                             # Top-right corner
            [-width/2, depth/2],                            # Top-left corner
            [-width/2, depth/2 - flange_thickness],         # Top-left flange bottom
            [-web_thickness/2, depth/2 - flange_thickness], # Left web top
            # Left side of web (top to bottom)
            [-web_thickness/2, -depth/2 + flange_thickness], # Left web bottom
            [-width/2, -depth/2 + flange_thickness]         # Bottom-left flange top
        ]

        vertices = []
        for frac in [0, 1]:
            origin = start + frac * length * direction
            for x, y in profile:
                point = origin + x * side + y * up
                vertices.append(point)

        num_pts = len(profile)
        x, y, z = zip(*vertices)

        i, j, k = [], [], []
        for n in range(num_pts):
            n_next = (n + 1) % num_pts
            i.append(n)
            j.append(n_next)
            k.append(n_next + num_pts)
            i.append(n)
            j.append(n_next + num_pts)
            k.append(n + num_pts)

        return x, y, z, i, j, k

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
