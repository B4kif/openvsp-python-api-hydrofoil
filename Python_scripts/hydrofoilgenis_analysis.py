import openvsp as vsp  # type: ignore

# ==============================================================================
# Parametric Settings for Hydrofoil Wing
# ==============================================================================
TOTAL_SPAN = 1.8         # Total span (m) — mirrored, so 0.9 per side
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
# ==============================================================================


def build_wing():
    """Build wing geometry and return wing_id."""
    wing_id = vsp.AddGeom("WING", "")
    vsp.SetGeomName(wing_id, "Main_Foil")

    half_span = TOTAL_SPAN / 2.0

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
    print(f"Wing built: span={TOTAL_SPAN}m, chord={CHORD}m, NACA 4412")
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


def run_analysis():
    """Main: build wing, run VSPAERO, extract and print results."""
    print("=" * 60)
    print("  HYDROFOIL VSPAERO ANALYSIS")
    print(f"  Span={TOTAL_SPAN}m  Chord={CHORD}m  AoA={AOA}deg")
    print(f"  V={VELOCITY}m/s  Re={RE:.0f}")
    print("=" * 60)

    vsp.ClearVSPModel()
    wing_id = build_wing()

    # Save model so VSPAERO files get proper base name
    vsp.WriteVSPFile(FILE_NAME)
    print(f"Saved: {FILE_NAME}")

    # Set reference wing
    vsp.SetVSPAERORefWingID(wing_id)
    print(f"Reference Wing ID: {wing_id}")

    # =============================================
    # STEP 1: VSPAEROComputeGeometry
    # =============================================
    # For VLM (thin lifting surfaces), the wing must be in ThinGeomSet.
    # GeomSet = thick surfaces (panel method) -> set to NOT_SHOWN (2) = empty
    # ThinGeomSet = thin surfaces (VLM) -> set to SET_ALL (0) = includes our wing
    cg_name = "VSPAEROComputeGeometry"
    vsp.SetAnalysisInputDefaults(cg_name)
    vsp.SetIntAnalysisInput(cg_name, "GeomSet", [2], 0)      # NOT_SHOWN = empty (no thick)
    vsp.SetIntAnalysisInput(cg_name, "ThinGeomSet", [0], 0)   # SET_ALL = wing as thin/VLM

    print("\n--- VSPAEROComputeGeometry inputs ---")
    vsp.PrintAnalysisInputs(cg_name)
    print("\nRunning ComputeGeometry...")
    cg_res = vsp.ExecAnalysis(cg_name)
    print(f"ComputeGeometry result: {cg_res}")

    # =============================================
    # STEP 2: VSPAEROSweep (single point)
    # =============================================
    sw_name = "VSPAEROSweep"
    vsp.SetAnalysisInputDefaults(sw_name)

    # Geometry sets: same as ComputeGeometry (thin VLM)
    vsp.SetIntAnalysisInput(sw_name, "GeomSet", [2], 0)       # no thick
    vsp.SetIntAnalysisInput(sw_name, "ThinGeomSet", [0], 0)    # wing as thin

    # Single AoA
    vsp.SetIntAnalysisInput(sw_name, "AlphaNpts", [1], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "AlphaStart", [AOA], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "AlphaEnd", [AOA], 0)

    # Beta = 0
    vsp.SetIntAnalysisInput(sw_name, "BetaNpts", [1], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "BetaStart", [0.0], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "BetaEnd", [0.0], 0)

    # Mach near-zero (incompressible water)
    vsp.SetIntAnalysisInput(sw_name, "MachNpts", [1], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "MachStart", [0.001], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "MachEnd", [0.001], 0)

    # Reynolds
    vsp.SetIntAnalysisInput(sw_name, "ReCrefNpts", [1], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "ReCrefStart", [RE], 0)
    vsp.SetDoubleAnalysisInput(sw_name, "ReCrefEnd", [RE], 0)

    # Reference: use component (RefFlag=1) with our wing
    vsp.SetIntAnalysisInput(sw_name, "RefFlag", [1], 0)
    vsp.SetStringAnalysisInput(sw_name, "WingID", [wing_id], 0)

    print("\n--- VSPAEROSweep inputs ---")
    vsp.PrintAnalysisInputs(sw_name)
    print(f"\nRunning VSPAEROSweep (AoA={AOA}, Mach=0.001, Re={RE:.0f})...")
    sweep_res = vsp.ExecAnalysis(sw_name)
    print(f"VSPAEROSweep result ID: {sweep_res}")

    # =============================================
    # STEP 3: Dump ALL result containers
    # =============================================
    dump_all_results()

    # =============================================
    # STEP 4: Extract results - try multiple containers
    # =============================================
    cl = 0.0
    cdi = 0.0
    cdtot = 0.0

    # Try 1: The sweep result itself
    print("--- Trying sweep result directly ---")
    cl_t, cdi_t, cdtot_t = extract_aero_results(sweep_res, "SweepResult")
    if cl_t != 0.0:
        cl, cdi, cdtot = cl_t, cdi_t, cdtot_t

    # Try 2: VSPAERO_Polar (integrated coefficients per flow condition)
    if cl == 0.0:
        print("\n--- Trying VSPAERO_Polar ---")
        try:
            polar_id = vsp.FindLatestResultsID("VSPAERO_Polar")
            if polar_id and polar_id != "":
                cl_t, cdi_t, cdtot_t = extract_aero_results(polar_id, "Polar")
                if cl_t != 0.0:
                    cl, cdi, cdtot = cl_t, cdi_t, cdtot_t
        except Exception as e:
            print(f"  VSPAERO_Polar not found: {e}")

    # Try 3: VSPAERO_History (iteration convergence - last value)
    if cl == 0.0:
        print("\n--- Trying VSPAERO_History ---")
        try:
            hist_id = vsp.FindLatestResultsID("VSPAERO_History")
            if hist_id and hist_id != "":
                cl_t, cdi_t, cdtot_t = extract_aero_results(hist_id, "History")
                if cl_t != 0.0:
                    cl, cdi, cdtot = cl_t, cdi_t, cdtot_t
        except Exception as e:
            print(f"  VSPAERO_History not found: {e}")

    # Try 4: Search ALL results for anything with CL
    if cl == 0.0:
        print("\n--- Searching ALL containers for CL ---")
        try:
            all_names = vsp.GetAllResultsNames()
            for rname in all_names:
                try:
                    rid = vsp.FindLatestResultsID(rname)
                    dnames = vsp.GetAllDataNames(rid)
                    if "CL" in dnames or "cl" in dnames:
                        cl_t, cdi_t, cdtot_t = extract_aero_results(rid, rname)
                        if cl_t != 0.0:
                            cl, cdi, cdtot = cl_t, cdi_t, cdtot_t
                            break
                except Exception:
                    pass
        except Exception:
            pass

    # If CDtot is zero but CDi is non-zero, use CDi as total
    if cdtot == 0.0 and cdi != 0.0:
        cdtot = cdi
    # If CDi is zero but CDtot is non-zero, use CDtot as CDi estimate
    if cdi == 0.0 and cdtot != 0.0:
        cdi = cdtot

    # =============================================
    # STEP 5: Compute forces
    # =============================================
    wing_area = TOTAL_SPAN * CHORD
    q = 0.5 * WATER_DENSITY * VELOCITY ** 2
    lift_N = q * wing_area * cl
    drag_N = q * wing_area * cdtot
    ld_ratio = cl / cdtot if cdtot != 0 else 0.0

    print("\n" + "=" * 60)
    print("  FINAL RESULTS")
    print("=" * 60)
    print(f"  Wing Area           = {wing_area:.4f} m2")
    print(f"  Dynamic Pressure    = {q:.1f} Pa")
    print(f"  AoA                 = {AOA} deg")
    print(f"")
    print(f"  CL                  = {cl:.6f}")
    print(f"  CDi (induced)       = {cdi:.6f}")
    print(f"  CD total            = {cdtot:.6f}")
    print(f"  L/D                 = {ld_ratio:.2f}")
    print(f"")
    print(f"  Lift Force          = {lift_N:.2f} N")
    print(f"  Drag Force          = {drag_N:.2f} N")
    print("=" * 60)

    return cl, cdtot, lift_N, drag_N


if __name__ == "__main__":
    run_analysis()