# Die Yield Calculator

This Streamlit application simulates die yield calculation on a wafer or panel. It allows you to configure substrate, reticle shot, die, and yield model settings, and then visualizes the results on a die map.

## Features

-   **Substrate Type Selection:** Choose between a wafer or a panel substrate.
-   **Configurable Dimensions:** Set substrate dimensions, reticle shot dimensions, die sizes, and scribe line gaps.
-   **Yield Model Options:** Choose from several yield models including Poisson, Murphy, Rectangular, Moore, and Seeds.
-   **Die Map Visualization:** Displays a color-coded die map showing good, defective, partial, and lost dice.
-   **Yield Results:** Provides summary of total, good, defective, partial and lost dice, along with calculated fab yield.

## How It Works

1.  **Tiling Reticle Shots:** The application tiles reticle shots across the substrate (wafer or panel).
2.  **Die Placement:** Calculates how many dice can be placed within each reticle shot including scribe-line gaps.
3.  **Boundary Check:** Checks each die’s corners against the substrate's boundary (or effective area).
4.  **Defect Simulation:** Simulates defects, and marks good physical dice as defective based on the selected yield model and defect rate.
5.  **Reporting:** Displays the final counts of good, defective, partial, and lost dice, and computes fab yield.
6.  **Visualization:** Generates a plot of the die map where:
    -   Good dice are green.
    -   Defective dice are red.
    -   Partial dice are yellow.
    -   Lost dice are grey.

## Usage

1.  Clone the repository or download the `app.py` file.
2.  Ensure you have Python and the required libraries (Streamlit, NumPy, Matplotlib, math, random) installed. You can install them using pip:

    ```bash
    pip install streamlit numpy matplotlib
    ```
3.  Run the Streamlit application:

    ```bash
    streamlit run app.py
    ```
4.  Open the application in your browser (usually at `http://localhost:8501`).
5.  Configure parameters on the sidebar:
    -   **Substrate Settings:** Select the substrate type, enter the diameter (for wafers), and the width and height (for panels). Also set the edge loss margin.
    -   **Reticle Shot Settings:** Enter the width and height of the reticle shot.
    -   **Die Settings:** Configure the width and height of each die, along with scribe-line spacing.
    -   **Yield Model Settings:** Set the defect rate, the critical area of the die and select the yield model to be used.
6.  Click the "Run Calculation" button.
7.  View the results summary and the die map visualization.

## Code Structure

-   `app.py`: Main Streamlit application file.
-   **Utility Functions:**
    -   `is_inside_wafer(x, y, effective_radius)`: Checks if a point is within a circle (wafer).
    -   `is_inside_panel(x, y, panel_width, panel_height, margin)`: Checks if a point is within the effective area of a panel.
    -   `compute_yield_fraction(defect_rate, critical_area, model)`: Calculates the yield fraction using the specified model.

## Dependencies

-   `streamlit`: For creating the web application.
-   `numpy`: For numerical computations.
-   `matplotlib`: For plotting.
-   `math`: For mathematical operations.
-   `random`: For defect injection simulation.

## Example

-   To run the simulation with the default values, simply click "Run Calculation" after starting the application.
-   Adjust different parameters to observe how they affect yield and die map visualization. For example:
    -   Increase the defect rate and see how more dice will be flagged as defective.
    -   Change the die size and observe the die map visualization and the final results.

## Notes

-   Edge loss can be set individually for wafers and panels and is the space from the edge of the substrate where dice cannot be placed.
-   Critical area represents the area that is sensitive to defects.
-   Experiment with different yield models to see how they affect the yield calculation.

This README provides a detailed overview of the application. Use it as a starting point for understanding and modifying the application to your specific needs.

