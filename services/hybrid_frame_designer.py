
import plotly.graph_objects as go
import numpy as np
from services.beam_service import BeamService

class HybridFrameDesigner:
    """Hybrid core + frame structure designer with parametric modeling capabilities"""
    
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
            'num_storeys': 3,
            'storey_height': 3.5,
            'core_width': 3.0,
            'core_depth': 3.0,
            'core_type': 'hollow',
            'core_wall_thickness': 0.4
        }
    
    def generate_hybrid_frame(self, parameters):
        """Generate a hybrid frame structure based on input parameters"""
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
            num_storeys = params.get('num_storeys', 3)
            storey_height = params.get('storey_height', params.get('column_height', 3.5))
            
            actual_length = num_bays_x * params['bay_spacing_x']
            actual_width = num_bays_y * params['bay_spacing_y']
            total_height = num_storeys * storey_height
            
            # Create hybrid frame using the attached code logic
            hybrid_frame = HybridFrame(
                width=actual_length,
                depth=actual_width,
                height=storey_height,
                storeys=num_storeys,
                bays_x=num_bays_x,
                bays_y=num_bays_y,
                beam_width=params['beam_width'],
                beam_depth=params['beam_depth']
            )
            
            # Create plotly figure
            fig = go.Figure(data=hybrid_frame.to_plotly())
            
            # Add shear core
            core_center = (hybrid_frame.width / 2, hybrid_frame.depth / 2)
            self.add_shear_core(
                fig, 
                core_center, 
                width=params['core_width'], 
                depth=params['core_depth'], 
                height=hybrid_frame.storeys * hybrid_frame.height, 
                core_type=params['core_type'],
                wall_thickness=params['core_wall_thickness']
            )
            
            # Add floor slabs
            for level in range(1, hybrid_frame.storeys + 1):
                self.add_floor_slab(fig, hybrid_frame.width, hybrid_frame.depth, level * hybrid_frame.height)
            
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
                title=f'Hybrid Structure with {params["core_type"].capitalize()} Core',
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            # Generate member metadata
            members = []
            member_id = 0
            
            # Add column metadata from hybrid frame
            for level in range(num_storeys):
                for start, end in hybrid_frame.get_column_positions(level):
                    member_id += 1
                    members.append({
                        'id': f'column_{member_id}',
                        'type': 'column',
                        'designation': f'Column {member_id}',
                        'cross_section': 'I-beam',
                        'length': np.linalg.norm(np.array(end) - np.array(start)),
                        'orientation': {
                            'horizontal_angle': 0,
                            'vertical_angle': 90
                        },
                        'dimensions': {
                            'width': params['column_width'],
                            'depth': params['column_depth']
                        },
                        'start_point': list(start),
                        'end_point': list(end)
                    })
            
            # Add beam metadata from hybrid frame
            for level in range(num_storeys):
                for start, end in hybrid_frame.get_beam_positions(level):
                    member_id += 1
                    direction = np.array(end) - np.array(start)
                    horizontal_angle = np.degrees(np.arctan2(direction[1], direction[0]))
                    
                    members.append({
                        'id': f'beam_{member_id}',
                        'type': 'beam',
                        'designation': f'Beam {member_id}',
                        'cross_section': 'I-beam',
                        'length': np.linalg.norm(direction),
                        'orientation': {
                            'horizontal_angle': horizontal_angle,
                            'vertical_angle': 0
                        },
                        'dimensions': {
                            'width': params['beam_width'],
                            'depth': params['beam_depth']
                        },
                        'start_point': list(start),
                        'end_point': list(end)
                    })
            
            # Calculate statistics
            total_columns = (num_bays_x + 1) * (num_bays_y + 1) * num_storeys
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
                'actual_width': actual_width,
                'core_type': params['core_type'],
                'core_dimensions': f"{params['core_width']}m x {params['core_depth']}m"
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

        # Create I-beam profile points
        top_flange = [[-width/2, depth/2], [width/2, depth/2],
                      [width/2, depth/2 - flange_thickness], [-width/2, depth/2 - flange_thickness]]
        web = [[-web_thickness/2, depth/2 - flange_thickness],
               [web_thickness/2, depth/2 - flange_thickness],
               [web_thickness/2, -depth/2 + flange_thickness],
               [-web_thickness/2, -depth/2 + flange_thickness]]
        bottom_flange = [[-width/2, -depth/2 + flange_thickness], [width/2, -depth/2 + flange_thickness],
                         [width/2, -depth/2], [-width/2, -depth/2]]
        profile = top_flange + web + bottom_flange

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

    def create_wall(self, x0, y0, x1, y1, z0, z1):
        """Create a wall panel"""
        vertices = [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                    [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]
        faces = [
            [0, 1, 2], [0, 2, 3], [4, 5, 6], [4, 6, 7],
            [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
            [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]
        ]
        x, y, z = zip(*vertices)
        i, j, k = zip(*faces)
        return go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color='lightgray', opacity=1.0, name='Core')

    def add_shear_core(self, fig, center, width, depth, height, core_type='solid', wall_thickness=0.4):
        """Add core with different geometry options"""
        cx, cy = center
        w2, d2 = width / 2, depth / 2
        x0, x1 = cx - w2, cx + w2
        y0, y1 = cy - d2, cy + d2
        z0, z1 = 0, height
        panels = []

        if core_type == 'solid':
            fig.add_trace(self.create_wall(x0, y0, x1, y1, z0, z1))

        elif core_type == 'hollow':
            t = wall_thickness
            panels = [
                self.create_wall(x0, y0, x0 + t, y1, z0, z1),
                self.create_wall(x1 - t, y0, x1, y1, z0, z1),
                self.create_wall(x0 + t, y0, x1 - t, y0 + t, z0, z1),
                self.create_wall(x0 + t, y1 - t, x1 - t, y1, z0, z1),
            ]

        elif core_type == 'u':
            t = wall_thickness
            panels = [
                self.create_wall(x0, y0, x0 + t, y1, z0, z1),
                self.create_wall(x1 - t, y0, x1, y1, z0, z1),
                self.create_wall(x0 + t, y0, x1 - t, y0 + t, z0, z1),
            ]

        elif core_type == 'l':
            t = wall_thickness
            panels = [
                self.create_wall(x0, y0, x0 + t, y1, z0, z1),
                self.create_wall(x0 + t, y1 - t, x1, y1, z0, z1),
            ]

        elif core_type == 'coupled':
            gap = 1.0
            t = wall_thickness
            wall_w = (width - gap) / 2
            wall_x0 = cx - width / 2
            wall_x1 = cx + gap / 2
            wall2_x0 = wall_x1 + gap
            wall2_x1 = wall2_x0 + wall_w
            panels = [
                self.create_wall(wall_x0, y0, wall_x1, y1, z0, z1),
                self.create_wall(wall2_x0, y0, wall2_x1, y1, z0, z1),
            ]

        for panel in panels:
            fig.add_trace(panel)

    def add_floor_slab(self, fig, width, depth, z, color='slategray'):
        """Add a floor slab"""
        x = [[0, width], [0, width]]
        y = [[0, 0], [depth, depth]]
        z_coords = [[z, z], [z, z]]
        fig.add_trace(go.Surface(x=x, y=y, z=z_coords, colorscale=[[0, color], [1, color]], showscale=False, opacity=0.5, name='Slab'))

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


class HybridFrame:
    """Frame builder class for hybrid core + frame system"""
    
    def __init__(self, width, depth, height, storeys, bays_x, bays_y, beam_width=0.3, beam_depth=0.5):
        self.width = width
        self.depth = depth
        self.height = height
        self.storeys = storeys
        self.bays_x = bays_x
        self.bays_y = bays_y
        self.beam_width = beam_width
        self.beam_depth = beam_depth
        self.bay_width = width / bays_x
        self.bay_depth = depth / bays_y
        self.designer = HybridFrameDesigner()

    def get_column_positions(self, level):
        """Get column positions for a given level"""
        z0 = level * self.height
        z1 = z0 + self.height
        return [((i * self.bay_width, j * self.bay_depth, z0),
                 (i * self.bay_width, j * self.bay_depth, z1))
                for i in range(self.bays_x + 1)
                for j in range(self.bays_y + 1)]

    def get_beam_positions(self, level):
        """Get beam positions for a given level"""
        z = (level + 1) * self.height
        beams = []
        # Y-direction beams
        for i in range(self.bays_x + 1):
            for j in range(self.bays_y):
                beams.append(((i * self.bay_width, j * self.bay_depth, z),
                              (i * self.bay_width, (j + 1) * self.bay_depth, z)))
        # X-direction beams
        for j in range(self.bays_y + 1):
            for i in range(self.bays_x):
                beams.append(((i * self.bay_width, j * self.bay_depth, z),
                              ((i + 1) * self.bay_width, j * self.bay_depth, z)))
        return beams

    def to_plotly(self):
        """Convert frame to plotly traces"""
        traces = []
        for level in range(self.storeys):
            # Add columns
            for start, end in self.get_column_positions(level):
                x, y, z, i, j, k = self.designer.generate_i_beam_mesh(start, end, self.beam_width, self.beam_depth)
                if x:  # Only add if mesh generation was successful
                    traces.append(go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color='gray', opacity=1.0, name='column'))
            
            # Add beams
            for start, end in self.get_beam_positions(level):
                x, y, z, i, j, k = self.designer.generate_i_beam_mesh(start, end, self.beam_width, self.beam_depth)
                if x:  # Only add if mesh generation was successful
                    traces.append(go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color='steelblue', opacity=1.0, name='beam'))
        
        return traces
