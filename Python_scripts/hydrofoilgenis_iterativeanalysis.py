import openvsp as vsp  # type: ignore
import pandas as pd  # type: ignore
import numpy as np  # type: ignore

# ==============================================================================
# Parametric Settings for Hydrofoil Wing
# ==============================================================================
# Span iteration
SPAN_START = 1.6         # Starting total span (m)
SPAN_END = 1.9           # Ending total span (m)
SPAN_STEP = 0.1          # Step size (m) -> 1.6, 1.7, 1.8, 1.9

CHORD = 0.3              # Chord (m)
THICKNESS_RATIO = 0.12   # 12% for NACA 4412
CAMBER = 0.04            # 4% camber
CAMBER_LOC = 0.4         # 40% camber location

# Winglet parameters
WINGLET_SPAN = 0.15      # Span of the winglet (m)
WINGLET_ANGLE = 10.0     # Dihedral angle of winglet (degrees)

# Flow conditions (water)
VELOCITY = 20.0          # m/s (~40 knots, typical foiling speed)
WATER_DENSITY = 1000.0   # kg/m^3
WATER_KIN_VISC = 1.0e-6  # m^2/s
RE = (VELOCITY * CHORD) / WATER_KIN_VISC  # = 6,000,000
AOA = 5.0                # Angle of attack (degrees)

FILE_NAME = "parametric_hydrofoil_wing.vsp3"
CSV_FILE = "hydrofoil_span_sweep_results.csv"
# ==============================================================================


def build_wing(total_span):
    """Build wing geometry for a given total span and return wing_id."""
    wing_id = vsp.AddGeom("WING", "")
    vsp.SetGeomName(wing_id, "Main_Foil")

    half_span = total_span / 2.0

    # Section 1: Main lifting surface
    vsp.SetParmVal(wing_id, "Span",       "XSec_1", half_span)
    vsp.SetParmVal(wing_id, "Root_Chord", "XSec_1", CHORD)
    vsp.SetParmVal(wing_id, "Tip_Chord",  "XSec_1", CHORD)
    vsp.SetParmVal(wing_id, "Sweep",      "XSec_1", 0.0)
    vsp.SetParmVal(wing_id, "Dihedral",   "XSec_1", 0.0)

    # Section 2: Winglet
    vsp.InsertXSec(wing_id, 1, vsp.XS_FOUR_SERIES)
    vsp.SetParmVal(wing_id, "Span",       "XSec_2", WINGLET_SPAN)
    vsp.SetParmVal(wing_id, "Root_Chord", "XSec_2", CHORD)
    vsp.SetParmVal(wing_id, "Tip_Chord",  "XSec_2", CHORD)
    vsp.SetParmVal(wing_id, "Dihedral",   "XSec_2", WINGLET_ANGLE)
    vsp.SetParmVal(wing_id, "Sweep",      "XSec_2", 0.0)

    # Cross-sections: all NACA 4412
    xsec_surf = vsp.GetXSecSurf(wing_id, 0)
    for idx in range(3):
        vsp.ChangeXSecShape(xsec_surf, idx, vsp.XS_FOUR_SERIES)
        xsec = vsp.GetXSec(xsec_surf, idx)
        for name, val in [("ThickChord", THICKNESS_RATIO),
                          ("Camber", CAMBER),
                          ("CamberLoc", CAMBER_LOC)]:
            pid = vsp.GetXSecParm(xsec, name)
            if pid:
                vsp.SetParmVal(pid, val)

    vsp.Update()
    return wing_id


def dump_all_results():
    """Print every result container and its data fields for debugging."""
    print("\n========== ALL RESULT CONTAINERS ==========")
    try:
        all_names = vsp.GetAllResultsNames()
        print(f"All result names: {all_names}")
        for rname in all_names:
            try:
                rid = vsp.FindLatestResultsID(rname)
                dnames = vsp.GetAllDataNames(rid)
                print(f"  '{rname}' -> id={rid}, fields={dnames}")
            except Exception as e:
                print(f"  '{rname}' -> ERROR: {e}")
    except Exception as e:
        print(f"  GetAllResultsNames failed: {e}")
    print("============================================\n")


def extract_aero_results(rid, label):
    """
    Extract CL, CDi, CDtot from a result container.
    Tries multiple field name variants defensively.
    Returns (cl, cdi, cdtot).
    """
    if not rid or rid == "":
        print(f"  [{label}] Empty result ID!")
        return 0.0, 0.0, 0.0

    try:
        dnames = vsp.GetAllDataNames(rid)
        print(f"  [{label}] ID={rid}")
        print(f"  [{label}] Fields: {dnames}")
    except Exception as e:
        print(f"  [{label}] Cannot get data names: {e}")
        return 0.0, 0.0, 0.0

    def get_last(field_candidates):
        for fname in field_candidates:
            if fname in dnames:
                try:
                    vec = vsp.GetDoubleResults(rid, fname)
                    if len(vec) > 0:
                        val = vec[-1]
                        print(f"    Found '{fname}': {vec} -> last={val}")
                        return val
                except Exception:
                    pass
        return 0.0

    cl = get_last(["CL", "cl", "CLtot", "CL_tot"])
    cdi = get_last(["CDi", "cdi", "CDind", "CD_ind"])
    cdtot = get_last(["CDtot", "CDTot", "cdtot", "CD", "cd", "CDt", "CD_tot"])

    return cl, cdi, cdtot


def analyze_single_span(total_span):
    """Build geometry, run VSPAERO, return (cl, cdi, cdtot, lift_N, drag_N)."""
    print(f"\n{'='*60}")
    print(f"  ANALYZING: Span = {total_span:.1f} m  |  AoA = {AOA} deg")
    print(f"{'='*60}")

    vsp.ClearVSPModel()
    wing_id = build_wing(total_span)
    vsp.WriteVSPFile(FILE_NAME)
    vsp.SetVSPAERORefWingID(wing_id)

    # ComputeGeometry (VLM thin surfaces)
    cg_name = "VSPAEROComputeGeometry"
    vsp.SetAnalysisInputDefaults(cg_name)
    vsp.SetIntAnalysisInput(cg_name, "GeomSet", [2], 0)
    vsp.SetIntAnalysisInput(cg_name, "ThinGeomSet", [0], 0)
    vsp.ExecAnalysis(cg_name)

    # VSPAEROSweep (single point)
    sw_name = "VSPAEROSweep"
    vsp.SetAnalysisInputDefaults(sw_name)
    vsp.SetIntAnalysisInput(sw_name, "GeomSet", [2], 0)
    vsp.SetIntAnalysisInput(sw_name, "ThinGeomSet", [0], 0)
    vsp.SetIntAnalysisInput(sw_name, "AlphaNpts", [1], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "AlphaStart", [AOA], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "AlphaEnd", [AOA], 0)
    vsp.SetIntAnalysisInput(sw_name, "BetaNpts", [1], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "BetaStart", [0.0], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "BetaEnd", [0.0], 0)
    vsp.SetIntAnalysisInput(sw_name, "MachNpts", [1], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "MachStart", [0.001], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "MachEnd", [0.001], 0)
    vsp.SetIntAnalysisInput(sw_name, "ReCrefNpts", [1], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "ReCrefStart", [RE], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "ReCrefEnd", [RE], 0)
    vsp.SetIntAnalysisInput(sw_name, "RefFlag", [1], 0)
    vsp.SetStringAnalysisInput(sw_name, "WingID", [wing_id], 0)
    vsp.ExecAnalysis(sw_name)

    # Extract from VSPAERO_Polar
    cl, cdi, cdtot = 0.0, 0.0, 0.0
    try:
        polar_id = vsp.FindLatestResultsID("VSPAERO_Polar")
        if polar_id and polar_id != "":
            cl, cdi, cdtot = extract_aero_results(polar_id, f"Span={total_span}")
    except Exception:
        pass

    # Fallback to History
    if cl == 0.0:
        try:
            hist_id = vsp.FindLatestResultsID("VSPAERO_History")
            if hist_id and hist_id != "":
                cl, cdi, cdtot = extract_aero_results(hist_id, f"Span={total_span}_Hist")
        except Exception:
            pass

    if cdtot == 0.0 and cdi != 0.0:
        cdtot = cdi
    if cdi == 0.0 and cdtot != 0.0:
        cdi = cdtot

    # Compute forces
    wing_area = total_span * CHORD
    q = 0.5 * WATER_DENSITY * VELOCITY ** 2
    lift_N = q * wing_area * cl
    drag_N = q * wing_area * cdtot

    print(f"  >> CL={cl:.4f}  CDtot={cdtot:.6f}  Lift={lift_N:.0f} N  Drag={drag_N:.0f} N")
    return cl, cdi, cdtot, lift_N, drag_N


def run_span_sweep():
    """Iterate over span values and display results in a pandas table."""
    spans = np.arange(SPAN_START, SPAN_END + SPAN_STEP / 2.0, SPAN_STEP)
    rows = []

    for span_val in spans:
        span_f = float(span_val)
        cl, cdi, cdtot, lift_N, drag_N = analyze_single_span(span_f)
        ld = float(cl / cdtot) if cdtot != 0 else 0.0
        area = float(span_f * CHORD)

        rows.append({
            "Span (m)":  float(f"{span_f:.1f}"),
            "Area (m²)": float(f"{area:.3f}"),
            "AoA (°)":   AOA,
            "CL":        float(f"{float(cl):.4f}"),
            "CDi":       float(f"{float(cdi):.6f}"),
            "CDtot":     float(f"{float(cdtot):.6f}"),
            "L/D":       float(f"{ld:.2f}"),
            "Lift (N)":  float(f"{float(lift_N):.1f}"),
            "Drag (N)":  float(f"{float(drag_N):.1f}"),
        })

    df = pd.DataFrame(rows)

    # Print formatted table
    header = (
        f"{'Span (m)':>10}  {'Area (m²)':>10}  {'AoA (°)':>8}  "
        f"{'CL':>8}  {'CDi':>10}  {'CDtot':>10}  "
        f"{'L/D':>8}  {'Lift (N)':>12}  {'Drag (N)':>12}"
    )
    sep = "-" * len(header)

    print("\n" + "=" * len(header))
    print("  HYDROFOIL SPAN SWEEP RESULTS")
    print(f"  V = {VELOCITY} m/s  |  AoA = {AOA}°  |  Chord = {CHORD} m  |  Re = {RE:.0f}")
    print("=" * len(header))
    print(header)
    print(sep)
    for _, row in df.iterrows():
        print(
            f"{row['Span (m)']:10.1f}  {row['Area (m²)']:10.3f}  {row['AoA (°)']:8.1f}  "
            f"{row['CL']:8.4f}  {row['CDi']:10.6f}  {row['CDtot']:10.6f}  "
            f"{row['L/D']:8.2f}  {row['Lift (N)']:12.1f}  {row['Drag (N)']:12.1f}"
        )
    print(sep)
    print("=" * len(header))

    df.to_csv(CSV_FILE, index=False)
    print(f"\nResults saved to '{CSV_FILE}'")

    vsp.WriteVSPFile(FILE_NAME)
    print(f"Final model saved to '{FILE_NAME}'")

    return df


if __name__ == "__main__":
    run_span_sweep()