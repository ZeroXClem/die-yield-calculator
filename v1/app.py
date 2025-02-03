import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import math
import random

# ============================
# Utility functions
# ============================

def is_inside_wafer(x, y, effective_radius):
    """Check if a point (x,y) is within a circle of radius effective_radius."""
    return (x**2 + y**2) <= effective_radius**2

def is_inside_panel(x, y, panel_width, panel_height, margin):
    """
    Check if a point (x,y) is inside the effective rectangular area of a panel.
    The effective area is defined as the full panel minus an edge-loss margin.
    """
    return (x >= margin) and (x <= panel_width - margin) and (y >= margin) and (y <= panel_height - margin)

def compute_yield_fraction(defect_rate, critical_area, model):
    """
    Compute the yield fraction using the specified model.
    The defect parameter D is computed as:
    
        D = defect_rate * (critical_area_in_cm2)
    
    where critical_area (input in mm²) is converted to cm² by dividing by 100.
    """
    D = defect_rate * (critical_area / 100)  # convert mm² to cm²
    if model == "Poisson":
        return math.exp(-D)
    elif model == "Murphy":
        return ((1 - math.exp(-D)) / D)**2 if D != 0 else 1.0
    elif model == "Rectangular":
        return (1 - math.exp(-2 * D)) / (2 * D) if D != 0 else 1.0
    elif model == "Moore":
        return math.exp(-math.sqrt(D))
    elif model == "Seeds":
        return 1 / (1 + D)
    else:
        return math.exp(-D)

# ============================
# Main App Function
# ============================

def main():
    st.title("Die Yield Calculator")
    st.write(
        """
        This app simulates the die‐yield calculation on a wafer (or panel) by:
        
        1. Tiling reticle shots over the substrate.
        2. Computing how many dice (with scribe-line gaps) can be placed in each shot.
        3. Checking each die’s corners against the substrate boundary (or effective area).
        4. Randomly marking some physically “good” dice as defective according to a yield model.
        5. Reporting final tallies and plotting a die map.
        """
    )
    
    # --------------------------
    # Sidebar: Substrate Settings
    # --------------------------
    st.sidebar.header("Substrate Settings")
    substrate_type = st.sidebar.selectbox("Select Substrate Type", ["Wafer", "Panel"])
    if substrate_type == "Wafer":
        wafer_diameter = st.sidebar.number_input("Wafer Diameter (mm)", value=300.0, step=1.0)
        edge_loss = st.sidebar.number_input("Edge Loss (mm)", value=0.0, step=0.5)
        radius = wafer_diameter / 2
        effective_radius = radius - edge_loss
    else:
        panel_width = st.sidebar.number_input("Panel Width (mm)", value=1000.0, step=10.0)
        panel_height = st.sidebar.number_input("Panel Height (mm)", value=500.0, step=10.0)
        edge_loss = st.sidebar.number_input("Edge Loss Margin (mm)", value=0.0, step=0.5)
    
    # --------------------------
    # Sidebar: Reticle Shot Settings
    # --------------------------
    st.sidebar.header("Reticle Shot Settings")
    shot_width = st.sidebar.number_input("Reticle Shot Width (mm)", value=26.0, step=1.0)
    shot_height = st.sidebar.number_input("Reticle Shot Height (mm)", value=33.0, step=1.0)
    
    # --------------------------
    # Sidebar: Die Settings
    # --------------------------
    st.sidebar.header("Die Settings")
    die_width = st.sidebar.number_input("Die Width (mm)", value=5.0, step=0.5)
    die_height = st.sidebar.number_input("Die Height (mm)", value=5.0, step=0.5)
    scribe_x = st.sidebar.number_input("Scribe Line (X) (mm)", value=0.2, step=0.1)
    scribe_y = st.sidebar.number_input("Scribe Line (Y) (mm)", value=0.2, step=0.1)
    
    # --------------------------
    # Sidebar: Yield Model Settings
    # --------------------------
    st.sidebar.header("Yield Model Settings")
    defect_rate = st.sidebar.number_input("Defect Rate (defects/cm²)", value=0.5, step=0.1)
    critical_area = st.sidebar.number_input("Critical Area (die area in mm²)", value=25.0, step=1.0)
    yield_model = st.sidebar.selectbox("Yield Model", ["Poisson", "Murphy", "Rectangular", "Moore", "Seeds"])
    
    # Button to run the calculation
    run = st.sidebar.button("Run Calculation")
    
    if run:
        # --------------------------
        # 1. Compute the yield fraction
        # --------------------------
        yld_fraction = compute_yield_fraction(defect_rate, critical_area, yield_model)
        
        # --------------------------
        # 2. Build the Die Grid over All Reticle Shots
        # --------------------------
        dice_list = []  # Each entry will be a dict with die position and status
        
        # For wafer: build a grid that covers the wafer's bounding box.
        # For panel: grid covers the full panel.
        if substrate_type == "Wafer":
            shot_x_positions = np.arange(-radius, radius, shot_width)
            shot_y_positions = np.arange(-radius, radius, shot_height)
        else:
            shot_x_positions = np.arange(0, panel_width, shot_width)
            shot_y_positions = np.arange(0, panel_height, shot_height)
        
        # Loop over each reticle shot
        for shot_x in shot_x_positions:
            for shot_y in shot_y_positions:
                # Compute how many dice fit horizontally and vertically in this shot.
                # (The scribe line is added to the die pitch.)
                num_dice_x = int((shot_width + scribe_x) // (die_width + scribe_x))
                num_dice_y = int((shot_height + scribe_y) // (die_height + scribe_y))
                
                # Place dice in a grid within the shot
                for i in range(num_dice_x):
                    for j in range(num_dice_y):
                        die_x = shot_x + i * (die_width + scribe_x)
                        die_y = shot_y + j * (die_height + scribe_y)
                        
                        # Define the four corners of the die rectangle.
                        corners = [
                            (die_x, die_y),
                            (die_x + die_width, die_y),
                            (die_x, die_y + die_height),
                            (die_x + die_width, die_y + die_height)
                        ]
                        
                        # Count how many corners lie within the substrate's effective region.
                        inside_count = 0
                        for (cx, cy) in corners:
                            if substrate_type == "Wafer":
                                if is_inside_wafer(cx, cy, effective_radius):
                                    inside_count += 1
                            else:  # Panel
                                if is_inside_panel(cx, cy, panel_width, panel_height, edge_loss):
                                    inside_count += 1
                        
                        # Classify the die based on how many corners are inside.
                        if inside_count == 4:
                            status = "good_physical"  # candidate for yield injection
                        elif inside_count > 0:
                            status = "partial"
                        else:
                            status = "lost"
                        
                        dice_list.append({
                            "x": die_x,
                            "y": die_y,
                            "status": status
                        })
        
        # --------------------------
        # 3. Defect Injection on Physically Good Dice
        # --------------------------
        # For dice that are fully inside, randomly mark some as defective.
        good_physical_indices = [idx for idx, d in enumerate(dice_list) if d["status"] == "good_physical"]
        num_good_physical = len(good_physical_indices)
        
        for idx in good_physical_indices:
            if random.random() < yld_fraction:
                dice_list[idx]["status"] = "good"
            else:
                dice_list[idx]["status"] = "defective"
        
        # --------------------------
        # 4. Tally the Results
        # --------------------------
        count_good = sum(1 for d in dice_list if d["status"] == "good")
        count_defective = sum(1 for d in dice_list if d["status"] == "defective")
        count_partial = sum(1 for d in dice_list if d["status"] == "partial")
        count_lost = sum(1 for d in dice_list if d["status"] == "lost")
        total_dice = len(dice_list)
        
        # Compute fab yield: good dice divided by the total of physically good dice
        fab_yield = (count_good / (count_good + count_defective)) if (count_good + count_defective) > 0 else 0
        
        st.subheader("Results Summary")
        st.write(f"**Total Dice (all shots):** {total_dice}")
        st.write(f"**Physically Good Dice (before defect injection):** {num_good_physical}")
        st.write(f"**Good Dice (after defect injection):** {count_good}")
        st.write(f"**Defective Dice:** {count_defective}")
        st.write(f"**Partial Dice:** {count_partial}")
        st.write(f"**Lost Dice:** {count_lost}")
        st.write(f"**Fab Yield (Good/(Good+Defective)):** {fab_yield:.2%}")
        
        # --------------------------
        # 5. Plot the Die Map
        # --------------------------
        fig, ax = plt.subplots()
        
        # Draw substrate boundary.
        if substrate_type == "Wafer":
            # The effective wafer is drawn as a dashed circle.
            circle = plt.Circle((0, 0), effective_radius, color='black', fill=False, linestyle='--')
            ax.add_artist(circle)
        else:
            # Draw the effective panel area (inner rectangle after edge loss).
            rect = plt.Rectangle((edge_loss, edge_loss),
                                 panel_width - 2 * edge_loss,
                                 panel_height - 2 * edge_loss,
                                 edgecolor='black', facecolor='none', linestyle='--')
            ax.add_artist(rect)
        
        # Draw each die as a colored rectangle.
        # Colors: Good = green, Defective = red, Partial = yellow, Lost = grey.
        for d in dice_list:
            if d["status"] == "good":
                color = "green"
            elif d["status"] == "defective":
                color = "red"
            elif d["status"] == "partial":
                color = "yellow"
            elif d["status"] == "lost":
                color = "grey"
            else:
                color = "blue"
            
            rect = plt.Rectangle((d["x"], d["y"]), die_width, die_height,
                                 edgecolor=color, facecolor=color, alpha=0.5)
            ax.add_patch(rect)
        
        ax.set_aspect('equal')
        if substrate_type == "Wafer":
            ax.set_xlim(-radius, radius)
            ax.set_ylim(-radius, radius)
            ax.set_title("Die Map on Wafer")
        else:
            ax.set_xlim(0, panel_width)
            ax.set_ylim(0, panel_height)
            ax.set_title("Die Map on Panel")
        
        st.pyplot(fig)

if __name__ == "__main__":
    main()
