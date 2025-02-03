import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import math, random, time
from io import BytesIO

# ============================
# Utility Functions
# ============================

def is_inside_wafer(x, y, effective_radius):
    """Return True if (x, y) lies within a circle of radius effective_radius."""
    return (x**2 + y**2) <= effective_radius**2

def is_inside_panel(x, y, panel_width, panel_height, margin):
    """Return True if (x, y) lies inside the effective panel area (panel minus margin)."""
    return (x >= margin) and (x <= panel_width - margin) and (y >= margin) and (y <= panel_height - margin)

def compute_yield_fraction(defect_rate, critical_area, model):
    """
    Compute the yield fraction using the specified model.
    The defect parameter D is computed as:
    
      D = defect_rate * (critical_area_in_cm2)
    
    where critical_area (mm²) is converted to cm² by dividing by 100.
    """
    D = defect_rate * (critical_area / 100.0)
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

# -----------------------------
# Cached Geometry Calculation
# -----------------------------
@st.cache_data(show_spinner=False)
def compute_geometry(substrate_type, substrate_params, shot_width, shot_height, die_width, die_height, scribe_x, scribe_y):
    """
    Compute the grid of die positions (their lower-left corners and corners list)
    across all reticle shots.
    
    Returns a list of dice, each represented as a dictionary:
      {
         "x": <die lower-left x>,
         "y": <die lower-left y>,
         "corners": [(x,y), ...] 4 corners,
         "status": "pending"  # classification later
      }
    """
    dice_positions = []
    
    if substrate_type == "Wafer":
        radius = substrate_params["radius"]
        shot_x_positions = np.arange(-radius, radius, shot_width)
        shot_y_positions = np.arange(-radius, radius, shot_height)
    else:  # Panel
        panel_width = substrate_params["panel_width"]
        panel_height = substrate_params["panel_height"]
        shot_x_positions = np.arange(0, panel_width, shot_width)
        shot_y_positions = np.arange(0, panel_height, shot_height)
    
    for shot_x in shot_x_positions:
        for shot_y in shot_y_positions:
            # Determine number of dice per shot (using integer division)
            num_dice_x = int((shot_width + scribe_x) // (die_width + scribe_x))
            num_dice_y = int((shot_height + scribe_y) // (die_height + scribe_y))
            
            for i in range(num_dice_x):
                for j in range(num_dice_y):
                    die_x = shot_x + i * (die_width + scribe_x)
                    die_y = shot_y + j * (die_height + scribe_y)
                    corners = [
                        (die_x, die_y),
                        (die_x + die_width, die_y),
                        (die_x, die_y + die_height),
                        (die_x + die_width, die_y + die_height)
                    ]
                    dice_positions.append({
                        "x": die_x,
                        "y": die_y,
                        "corners": corners,
                        "status": "pending"
                    })
    return dice_positions

def classify_die(die, substrate_type, substrate_params):
    """Classify a die based on its corner positions."""
    inside_count = 0
    for (cx, cy) in die["corners"]:
        if substrate_type == "Wafer":
            if is_inside_wafer(cx, cy, substrate_params["effective_radius"]):
                inside_count += 1
        else:
            if is_inside_panel(cx, cy, substrate_params["panel_width"], substrate_params["panel_height"], substrate_params["edge_loss"]):
                inside_count += 1
    if inside_count == 4:
        return "good_physical"
    elif inside_count > 0:
        return "partial"
    else:
        return "lost"

def inject_defects(dice_list, yield_fraction, seed=None):
    """
    For each die that is physically good, mark it as "good" or "defective" using the yield_fraction.
    A random seed can be set for reproducibility.
    """
    if seed is not None:
        random.seed(seed)
    for d in dice_list:
        if d["status"] == "good_physical":
            d["status"] = "good" if random.random() < yield_fraction else "defective"
    return dice_list

def run_simulation(sim_runs, base_dice, substrate_type, substrate_params, yield_fraction, random_seed):
    """
    Run the defect injection simulation multiple times (Monte Carlo) and return aggregated results.
    """
    sim_results = []
    for run in range(sim_runs):
        # Deep copy the base dice for each simulation run
        dice_copy = [d.copy() for d in base_dice]
        # Classify each die (in case geometry wasn’t updated)
        for d in dice_copy:
            d["status"] = classify_die(d, substrate_type, substrate_params)
        dice_with_defects = inject_defects(dice_copy, yield_fraction, seed=random_seed + run if random_seed is not None else None)
        # Tally results
        count_good = sum(1 for d in dice_with_defects if d["status"] == "good")
        count_defective = sum(1 for d in dice_with_defects if d["status"] == "defective")
        count_partial = sum(1 for d in dice_with_defects if d["status"] == "partial")
        count_lost = sum(1 for d in dice_with_defects if d["status"] == "lost")
        fab_yield = (count_good / (count_good + count_defective)) if (count_good + count_defective) > 0 else 0
        sim_results.append({
            "total": len(dice_with_defects),
            "good_physical": sum(1 for d in dice_with_defects if d["status"] in ["good", "defective"]),
            "good": count_good,
            "defective": count_defective,
            "partial": count_partial,
            "lost": count_lost,
            "fab_yield": fab_yield,
            "dice": dice_with_defects
        })
    return sim_results

# ============================
# Main App
# ============================

def main():
    st.set_page_config(page_title="Advanced Die Yield Calculator", layout="wide")
    st.title("Advanced Die Yield Calculator")
    st.markdown(
        """
        This interactive app simulates the die-yield process for semiconductor substrates.
        
        **Features:**
        - Supports both wafer (circular) and panel (rectangular) geometries.
        - Tiles reticle shots, calculates die positions (with scribe-line gaps), and classifies dies as fully inside, partial, or lost.
        - Injects defects into physically good dies based on user-selected yield models.
        - Offers a Monte Carlo simulation mode to explore variability in fab yield.
        - Enhanced UI with adjustable random seed, extra visualization options, and detailed summary outputs.
        """
    )

    # -------------------------
    # Sidebar: Simulation Options
    # -------------------------
    st.sidebar.header("1. Substrate & Geometry Settings")
    substrate_type = st.sidebar.selectbox("Substrate Type", ["Wafer", "Panel"])

    # Substrate-specific parameters
    if substrate_type == "Wafer":
        wafer_diameter = st.sidebar.number_input("Wafer Diameter (mm)", value=300.0, step=1.0)
        edge_loss = st.sidebar.number_input("Wafer Edge Loss (mm)", value=0.0, step=0.5)
        radius = wafer_diameter / 2
        effective_radius = radius - edge_loss
        substrate_params = {"radius": radius, "effective_radius": effective_radius}
    else:
        panel_width = st.sidebar.number_input("Panel Width (mm)", value=1000.0, step=10.0)
        panel_height = st.sidebar.number_input("Panel Height (mm)", value=500.0, step=10.0)
        edge_loss = st.sidebar.number_input("Panel Edge Loss Margin (mm)", value=0.0, step=0.5)
        substrate_params = {"panel_width": panel_width, "panel_height": panel_height, "edge_loss": edge_loss}

    st.sidebar.markdown("---")
    st.sidebar.header("2. Reticle & Die Settings")
    shot_width = st.sidebar.number_input("Reticle Shot Width (mm)", value=26.0, step=1.0)
    shot_height = st.sidebar.number_input("Reticle Shot Height (mm)", value=33.0, step=1.0)
    die_width = st.sidebar.number_input("Die Width (mm)", value=5.0, step=0.5)
    die_height = st.sidebar.number_input("Die Height (mm)", value=5.0, step=0.5)
    scribe_x = st.sidebar.number_input("Scribe Line (X) (mm)", value=0.2, step=0.1)
    scribe_y = st.sidebar.number_input("Scribe Line (Y) (mm)", value=0.2, step=0.1)

    st.sidebar.markdown("---")
    st.sidebar.header("3. Yield Model Settings")
    defect_rate = st.sidebar.number_input("Defect Rate (defects/cm²)", value=0.5, step=0.1)
    critical_area = st.sidebar.number_input("Critical Area (mm²)", value=25.0, step=1.0)
    yield_model = st.sidebar.selectbox("Yield Model", ["Poisson", "Murphy", "Rectangular", "Moore", "Seeds"])
    yield_fraction = compute_yield_fraction(defect_rate, critical_area, yield_model)
    st.sidebar.info(f"Calculated yield fraction: {yield_fraction:.3f}")

    st.sidebar.markdown("---")
    st.sidebar.header("4. Simulation Options")
    sim_runs = st.sidebar.slider("Number of Monte Carlo Runs", min_value=1, max_value=20, value=1, step=1)
    random_seed = st.sidebar.number_input("Random Seed (for reproducibility)", value=42, step=1)
    show_shots = st.sidebar.checkbox("Show Reticle Shot Boundaries", value=False)

    # Button to trigger simulation
    if st.sidebar.button("Run Simulation"):
        start_time = time.time()

        # Compute the base geometry (cached for performance)
        base_dice = compute_geometry(substrate_type, substrate_params, shot_width, shot_height, die_width, die_height, scribe_x, scribe_y)
        # Classify each die based on geometry
        for d in base_dice:
            d["status"] = classify_die(d, substrate_type, substrate_params)
        
        # Run Monte Carlo simulation (even if only one run)
        sim_results = run_simulation(sim_runs, base_dice, substrate_type, substrate_params, yield_fraction, random_seed)
        
        # If multiple runs, compute averages
        avg_fab_yield = np.mean([r["fab_yield"] for r in sim_results])
        st.subheader("Simulation Results Summary")
        st.write(f"**Number of Monte Carlo Runs:** {sim_runs}")
        st.write(f"**Average Fab Yield:** {avg_fab_yield:.2%}")
        
        # For detailed output, show results of the first run
        result = sim_results[0]
        st.markdown("#### Detailed Tally (from first simulation run)")
        st.write(f"**Total Dice (all shots):** {result['total']}")
        st.write(f"**Physically Good Dice (before defect injection):** {result['good_physical']}")
        st.write(f"**Good Dice (after defect injection):** {result['good']}")
        st.write(f"**Defective Dice:** {result['defective']}")
        st.write(f"**Partial Dice:** {result['partial']}")
        st.write(f"**Lost Dice:** {result['lost']}")
        st.write(f"**Fab Yield (Good/(Good+Defective)):** {result['fab_yield']:.2%}")
        
        sim_time = time.time() - start_time
        st.info(f"Simulation completed in {sim_time:.2f} seconds.")

        # -------------------------
        # Plotting the Die Map
        # -------------------------
        st.markdown("#### Die Map Visualization")
        fig, ax = plt.subplots(figsize=(8, 8))
        
        # Draw substrate boundary
        if substrate_type == "Wafer":
            circle = plt.Circle((0, 0), substrate_params["effective_radius"], color='black', 
                                fill=False, linestyle='--', label="Wafer Boundary")
            ax.add_artist(circle)
        else:
            rect = plt.Rectangle((substrate_params["edge_loss"], substrate_params["edge_loss"]),
                                 substrate_params["panel_width"] - 2 * substrate_params["edge_loss"],
                                 substrate_params["panel_height"] - 2 * substrate_params["edge_loss"],
                                 edgecolor='black', facecolor='none', linestyle='--', label="Panel Effective Area")
            ax.add_artist(rect)
        
        # Optionally, draw reticle shot boundaries
        if show_shots:
            if substrate_type == "Wafer":
                radius = substrate_params["radius"]
                shot_x_positions = np.arange(-radius, radius, shot_width)
                shot_y_positions = np.arange(-radius, radius, shot_height)
            else:
                shot_x_positions = np.arange(0, substrate_params["panel_width"], shot_width)
                shot_y_positions = np.arange(0, substrate_params["panel_height"], shot_height)
            for sx in shot_x_positions:
                rect_shot = plt.Rectangle((sx, shot_y_positions[0]), shot_width, shot_height * len(shot_y_positions),
                                          edgecolor='blue', facecolor='none', linestyle=':', alpha=0.3)
                ax.add_patch(rect_shot)
            for sy in shot_y_positions:
                rect_shot = plt.Rectangle((shot_x_positions[0], sy), shot_width * len(shot_x_positions), shot_height,
                                          edgecolor='blue', facecolor='none', linestyle=':', alpha=0.3)
                ax.add_patch(rect_shot)
        
        # Draw each die as a colored rectangle.
        # Colors: Good = green, Defective = red, Partial = yellow, Lost = grey.
        for d in result["dice"]:
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
            rect_die = plt.Rectangle((d["x"], d["y"]), die_width, die_height,
                                     edgecolor=color, facecolor=color, alpha=0.5)
            ax.add_patch(rect_die)
        
        ax.set_aspect('equal')
        if substrate_type == "Wafer":
            ax.set_xlim(-substrate_params["radius"], substrate_params["radius"])
            ax.set_ylim(-substrate_params["radius"], substrate_params["radius"])
            ax.set_title("Die Map on Wafer")
        else:
            ax.set_xlim(0, substrate_params["panel_width"])
            ax.set_ylim(0, substrate_params["panel_height"])
            ax.set_title("Die Map on Panel")
        
        # Display the plot in Streamlit
        st.pyplot(fig)
        
        # -------------------------
        # Offer download of the plot image using a BytesIO buffer
        # -------------------------
        buf = BytesIO()
        fig.canvas.print_png(buf)  # Write PNG data into the buffer
        buf.seek(0)  # Reset the buffer's position to the beginning
        st.download_button(
            "Download Plot as PNG",
            data=buf,
            file_name="die_map.png",
            mime="image/png"
        )

    # -------------------------
    # Additional Information
    # -------------------------
    with st.expander("About This App"):
        st.markdown(
            """
            **Overview:**
            
            This app simulates the process of tiling dies over a wafer or panel and evaluates yield 
            based on various defect models. The simulation includes:
            
            - **Geometry Calculation:** Partitioning the substrate into reticle shots and determining 
              die positions (including scribe lines).
            - **Die Classification:** Using a corner-based approach to determine if a die is fully within 
              the effective area, partially in, or lost.
            - **Yield Injection:** Randomly marking physically good dies as defective based on the 
              specified yield model and defect rate.
            - **Monte Carlo Simulation:** Optionally running multiple iterations to explore variability.
            
            **Optimizations and Features:**
            
            - **Caching:** Geometry calculations are cached to improve performance when parameters remain unchanged.
            - **UI Enhancements:** Adjustable simulation options, reticle boundary display, and reproducible random seeds.
            - **Downloadable Visuals:** Save the die map as a PNG image.
            
            Enjoy exploring and tweaking parameters to see how different yield models and geometries affect your fab yield!
            """
        )

if __name__ == "__main__":
    main()

