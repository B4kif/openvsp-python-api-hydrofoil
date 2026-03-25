import openvsp as vsp
import sys

# ==============================================================================
# Parametric Settings for Hydrofoil Wing
# ==============================================================================
SPAN_SEC1 = 0.4          # Span of section 1 on one side (Total span = 0.8m)
CHORD = (SPAN_SEC1 * 2) / 5.0 # Span/Chord ratio = 5 (Calculates to 0.16m)
THICKNESS_RATIO = 0.12   # Thickness-to-chord ratio (0.12 = 12% for NACA 4412)
CAMBER = 0.04            # Maximum camber (0.04 = 4% for NACA 4412)
CAMBER_LOC = 0.4         # Location of maximum camber (0.4 = 40% for NACA 4412)

# Winglet parameters
WINGLET_SPAN = 0.15      # Span (x) of the winglet
WINGLET_ANGLE = 10.0     # Dihedral angle (a) of the winglet in degrees

# Set to True to save the resulting .vsp3 file
SAVE_FILE = True
FILE_NAME = "parametric_hydrofoil_wing.vsp3"
# ==============================================================================

def create_parametric_wing():
    print("Clearing OpenVSP Model...")
    vsp.ClearVSPModel()
    
    print("Adding Wing Geometry...")
    wing_id = vsp.AddGeom("WING", "")
    vsp.SetGeomName(wing_id, "Main_Foil")
    
    # -----------------------------------------------------
    # 1. Main Wing Planform
    # Section 1: Main lifting surface.
    # Section 2: Downward pointing winglet.
    # -----------------------------------------------------
    print("Applying Planform Parameters...")
    
    # The main horizontal span is dictated by the SPAN_SEC1 variable.
    span_sec1 = SPAN_SEC1
    span_sec2 = WINGLET_SPAN
    
    # -----------------------------------------------------
    # Main Section 1
    # -----------------------------------------------------
    vsp.SetParmVal(wing_id, "Span", "XSec_1", span_sec1)
    vsp.SetParmVal(wing_id, "Root_Chord", "XSec_1", CHORD)
    vsp.SetParmVal(wing_id, "Tip_Chord", "XSec_1", CHORD)
    vsp.SetParmVal(wing_id, "Sweep", "XSec_1", 0.0)      
    vsp.SetParmVal(wing_id, "Dihedral", "XSec_1", 0.0)   
    
    # -----------------------------------------------------
    # Winglet Section 2
    # -----------------------------------------------------
    print("Adding Winglet Section...")
    vsp.InsertXSec(wing_id, 1, vsp.XS_FOUR_SERIES) 
    
    vsp.SetParmVal(wing_id, "Span", "XSec_2", span_sec2) 
    vsp.SetParmVal(wing_id, "Root_Chord", "XSec_2", CHORD)  
    vsp.SetParmVal(wing_id, "Tip_Chord", "XSec_2", CHORD)   
    vsp.SetParmVal(wing_id, "Dihedral", "XSec_2", WINGLET_ANGLE)
    vsp.SetParmVal(wing_id, "Sweep", "XSec_2", 0.0)
    
    # -----------------------------------------------------
    # 3. Apply Cross-Section Profiles (NACA 4-Series to Rounded Rectangle)
    # -----------------------------------------------------
    xsec_surf = vsp.GetXSecSurf(wing_id, 0)
    
    # Now we have 3 cross sections to define: 
    # 0 (Root), 1 (Tip Inboard), 2 (Tip Outboard)
    vsp.ChangeXSecShape(xsec_surf, 0, vsp.XS_FOUR_SERIES)
    vsp.ChangeXSecShape(xsec_surf, 1, vsp.XS_FOUR_SERIES)
    vsp.ChangeXSecShape(xsec_surf, 2, vsp.XS_FOUR_SERIES)
    
    # Helper function to safely set parameter by name for an XSec
    def set_xsec_parm(xsec_obj, parm_name, val):
        parm_id = vsp.GetXSecParm(xsec_obj, parm_name)
        if parm_id != "":
            vsp.SetParmVal(parm_id, val)

    # Set the parameters for each section
    for idx in [0, 1, 2]:
        xsec = vsp.GetXSec(xsec_surf, idx)
        
        # All sections: NACA 4412
        set_xsec_parm(xsec, "ThickChord", THICKNESS_RATIO)
        set_xsec_parm(xsec, "Thickness", THICKNESS_RATIO) 
        set_xsec_parm(xsec, "Camber", CAMBER)
        set_xsec_parm(xsec, "CamberLoc", CAMBER_LOC)

    print("Updating UI Geometry...")
    vsp.Update()
    
    if SAVE_FILE:
        print(f"Saving OpenVSP model to '{FILE_NAME}'...")
        vsp.WriteVSPFile(FILE_NAME)
        print("Done! You can open the saved file in OpenVSP.")

if __name__ == "__main__":
    create_parametric_wing()
