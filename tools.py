from agents import function_tool
import os
from openai import OpenAI


@function_tool
def calculate_area_load(
    thickness_m: float,
    density_kN_per_m3: float,
    description: str = "",
    standard: str = "NZS 1170.1"
) -> dict:
    """
    Calculates area dead load (kPa) from thickness and density.

    Args:
      thickness_m: Thickness of the material (m)
      density_kN_per_m3: Density of the material (kN/m³)
      description: Description of the material (optional)
      standard: Standard reference (default NZS 1170.1)

    Returns:
      area_load_kPa, calculation_steps, standard_reference
    """
    area_load_kPa = thickness_m * density_kN_per_m3
    steps = [
        f"Area load = thickness × density = {thickness_m} × {density_kN_per_m3} = {area_load_kPa:.2f} kPa"
    ]
    return {
        "inputs": {
            "thickness_m": thickness_m,
            "density_kN_per_m3": density_kN_per_m3,
            "description": description,
            "standard": standard
        },
        "area_load_kPa": area_load_kPa,
        "calculation_steps": steps,
        "standard_reference": f"{standard} Table 3.1"
    }


@function_tool
def calculate_line_load(
    area_load_kPa: float,
    tributary_width_m: float,
    description: str = "",
    standard: str = "NZS 1170.1"
) -> dict:
    """
    Converts area load (kPa) to line load (kN/m) for a given tributary width.

    Args:
      area_load_kPa: Area load (kPa)
      tributary_width_m: Tributary width (m)
      description: Description of the load (optional)
      standard: Standard reference (default NZS 1170.1)

    Returns:
      line_load_kN_per_m, calculation_steps, standard_reference
    """
    line_load_kN_per_m = area_load_kPa * tributary_width_m
    steps = [
        f"Line load = area_load × tributary_width = {area_load_kPa} × {tributary_width_m} = {line_load_kN_per_m:.2f} kN/m"
    ]
    return {
        "inputs": {
            "area_load_kPa": area_load_kPa,
            "tributary_width_m": tributary_width_m,
            "description": description,
            "standard": standard
        },
        "line_load_kN_per_m": line_load_kN_per_m,
        "calculation_steps": steps,
        "standard_reference": f"{standard} Section 4"
    }


@function_tool
def combine_line_loads(
    dead_line_load_kN_per_m: float,
    live_line_load_kN_per_m: float = 0.0,
    dead_factor: float = 1.2,
    live_factor: float = 1.5,
    combo_label: str = "ULS_1.2G+1.5Q",
    standard: str = "NZS 1170.1"
) -> dict:
    """
    Combines dead and live line loads using specified factors.
    Args:
      dead_line_load_kN_per_m: Dead load (kN/m)
      live_line_load_kN_per_m: Live load (kN/m)
      dead_factor: Factor for dead load (default 1.2)
      live_factor: Factor for live load (default 1.5)
      combo_label: Description of combination (e.g. ULS, SLS)
      standard: Reference standard
    Returns:
      combo_line_load_kN_per_m, calculation_steps, standard_reference
    """
    combo = dead_factor * dead_line_load_kN_per_m + live_factor * live_line_load_kN_per_m
    steps = [
        f"{combo_label}: {dead_factor} × {dead_line_load_kN_per_m} + {live_factor} × {live_line_load_kN_per_m} = {combo:.2f} kN/m"
    ]
    return {
        "inputs": {
            "dead_line_load_kN_per_m": dead_line_load_kN_per_m,
            "live_line_load_kN_per_m": live_line_load_kN_per_m,
            "dead_factor": dead_factor,
            "live_factor": live_factor,
            "combo_label": combo_label,
            "standard": standard
        },
        "combo_line_load_kN_per_m": combo,
        "calculation_steps": steps,
        "standard_reference": f"{standard} (factors: {dead_factor}G, {live_factor}Q)"
    }


@function_tool
def calculate_max_moment(
    line_load_kN_per_m: float,
    span_m: float,
    description: str = "",
    formula_type: str = "simply_supported_udl",
    standard: str = "NZS 1170.1"
) -> dict:
    """
    Calculates max bending moment for a beam.
    Args:
      line_load_kN_per_m: Uniform line load (kN/m)
      span_m: Beam span (m)
      description: Optional
      formula_type: Type of moment formula to use (default is simply supported with UDL)
      standard: Reference standard
    Returns:
      max_moment_kNm, calculation_steps, standard_reference
    """
    if formula_type == "simply_supported_udl":
        max_moment_kNm = line_load_kN_per_m * span_m ** 2 / 8
        formula_desc = "w × L² / 8"
    else:
        return {"error": f"Unsupported formula_type: {formula_type}"}
    steps = [
        f"Max moment = {formula_desc} = {line_load_kN_per_m} × {span_m}² / 8 = {max_moment_kNm:.2f} kNm"
    ]
    return {
        "inputs": {
            "line_load_kN_per_m": line_load_kN_per_m,
            "span_m": span_m,
            "description": description,
            "formula_type": formula_type,
            "standard": standard
        },
        "max_moment_kNm": max_moment_kNm,
        "calculation_steps": steps,
        "standard_reference": f"{standard} Section 6.3"
    }


@function_tool
def calculate_max_shear(
    line_load_kN_per_m: float,
    span_m: float,
    description: str = "",
    formula_type: str = "simply_supported_udl",
    standard: str = "NZS 1170.1"
) -> dict:
    """
    Calculates max shear force for a beam.
    Args:
      line_load_kN_per_m: Uniform line load (kN/m)
      span_m: Beam span (m)
      description: Optional
      formula_type: Type of shear formula to use (default is simply supported with UDL)
      standard: Reference standard
    Returns:
      max_shear_kN, calculation_steps, standard_reference
    """
    if formula_type == "simply_supported_udl":
        max_shear_kN = line_load_kN_per_m * span_m / 2
        formula_desc = "w × L / 2"
    else:
        return {"error": f"Unsupported formula_type: {formula_type}"}
    steps = [
        f"Max shear = {formula_desc} = {line_load_kN_per_m} × {span_m} / 2 = {max_shear_kN:.2f} kN"
    ]
    return {
        "inputs": {
            "line_load_kN_per_m": line_load_kN_per_m,
            "span_m": span_m,
            "description": description,
            "formula_type": formula_type,
            "standard": standard
        },
        "max_shear_kN": max_shear_kN,
        "calculation_steps": steps,
        "standard_reference": f"{standard} Section 6.3"
    }


@function_tool
def list_calculation_tools() -> dict:
    """
    Returns a list and description of all calculation tools (function tools) currently available.
    Use this to check what calculations are supported by the Calculation Agent.
    """
    return {
        "supported_calculations": [
            {
                "name": "calculate_area_load",
                "description": (
                    "Calculates area load (kPa) from material thickness and density. "
                    "Inputs: thickness_m (m), density_kN_per_m3 (kN/m³), "
                    "description (optional), standard (optional, default NZS 1170.1)."
                )
            },
            {
                "name": "calculate_line_load",
                "description": (
                    "Converts area load (kPa) to line load (kN/m) for a given tributary width. "
                    "Inputs: area_load_kPa (kPa), tributary_width_m (m), "
                    "description (optional), standard (optional, default NZS 1170.1)."
                )
            },
            {
                "name": "combine_line_loads",
                "description": (
                    "Combines dead and live line loads using specified factors for load combinations. "
                    "Inputs: dead_line_load_kN_per_m (kN/m), live_line_load_kN_per_m (kN/m, optional), "
                    "dead_factor (default 1.2), live_factor (default 1.5), "
                    "combo_label (optional), standard (optional, default NZS 1170.1)."
                )
            },
            {
                "name": "calculate_max_moment",
                "description": (
                    "Calculates the maximum bending moment (kNm) for a beam with a uniformly distributed load. "
                    "Inputs: line_load_kN_per_m (kN/m), span_m (m), "
                    "description (optional), formula_type (default 'simply_supported_udl'), "
                    "standard (optional, default NZS 1170.1)."
                )
            },
            {
                "name": "calculate_max_shear",
                "description": (
                    "Calculates the maximum shear force (kN) for a beam with a uniformly distributed load. "
                    "Inputs: line_load_kN_per_m (kN/m), span_m (m), "
                    "description (optional), formula_type (default 'simply_supported_udl'), "
                    "standard (optional, default NZS 1170.1)."
                )
            }
        ]
    }

@function_tool
def list_accessible_standards() -> list[dict]:
    """
    Lists all standard documents available (from a static dictionary).
    Returns:
        list of dict: Each item is {"standard": str, "description": str}
    """

    # Dictionary mapping: code -> description
    nz_standards = {
        "NZS 3404:1997": "Steel Structures Standard – Parts 1 & 2: sets minimum requirements for limit‐state design, fabrication, erection, and modification of steelwork in structures.",
        "Building Code Handbook 3E Amdt13": "Comprehensive companion to the NZ Building Code, providing guidance, explanatory commentary, and cross‑referenced design examples.",
        "NZS 1170.5:2004": "Structural Design Actions – Part 5: Earthquake Actions: specifies procedures to determine seismic design actions for NZ buildings (excludes Amendment 1).",
        "NZS 3605:2001": "Timber Piles & Poles: sets performance criteria and means of compliance for timber piles and poles used in buildings, referenced in NZS 3604.",
        "NZS 4219:2009": "Seismic Performance of Engineering Systems: covers design and installation of seismic restraints for non‑structural building services (e.g., ducts, tanks, pipework).",
        "NZS 4121:2001": "Design for Access & Mobility: sets requirements for accessible built environments (entrances, pathways, fixtures) in compliance with Building Code accessibility clauses.",
        "SNZ‑TS 3404:2018": "Durability Requirements for Steel Structures: technical spec complementing NZS 3404, defining coating and corrosion protection for steel in different environments.",
        "NZS 3604:2011": "Timber‑Framed Buildings: guidance for design and construction of light timber‑framed houses and small buildings (up to 3 storeys) on good ground.",
        "NZS 3101:2006": "Concrete Structures – Part 1 (with Amendments A1‑A3): sets minimum requirements for design of reinforced and prestressed concrete structures.",
    }
    return [{"standard": code, "description": desc} for code, desc in nz_standards.items()]