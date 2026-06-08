"""
House Style for Plots

This module defines the standard plotting style for all visualizations in the project.

Style Guidelines:
- Large, readable axis text fonts
- UChicago maroon (#800000) as the base color
- Sparse/bare gridlines
- Clean, professional appearance

Usage:
    import matplotlib.pyplot as plt
    from plot_style import apply_plot_style, UCHICAGO_MAROON

    apply_plot_style()

    # Create your plot
    fig, ax = plt.subplots()
    ax.plot(x, y, color=UCHICAGO_MAROON)
    # ... rest of plot code
"""

import matplotlib.pyplot as plt
import matplotlib as mpl

# Define UChicago maroon color
UCHICAGO_MAROON = '#800000'

# Extended color palette with high contrast
# Based on maroon but with distinct, easily distinguishable colors
COLOR_PALETTE = [
    '#800000',  # UChicago maroon (base)
    '#E69F00',  # Orange/gold (high contrast)
    '#0072B2',  # Blue (colorblind-safe)
    '#009E73',  # Teal/green (colorblind-safe)
    '#CC79A7',  # Pink/mauve
    '#56B4E9',  # Light blue
    '#D55E00',  # Vermillion/red-orange
    '#F0E442',  # Yellow
    '#999999',  # Gray
]


def apply_plot_style():
    """
    Apply the house plotting style to all matplotlib plots.

    This function sets matplotlib rcParams to create consistent,
    professional-looking plots across the project.
    """

    # Font sizes
    plt.rcParams['font.size'] = 12
    plt.rcParams['axes.titlesize'] = 16
    plt.rcParams['axes.labelsize'] = 14
    plt.rcParams['xtick.labelsize'] = 12
    plt.rcParams['ytick.labelsize'] = 12
    plt.rcParams['legend.fontsize'] = 12
    plt.rcParams['figure.titlesize'] = 18

    # Colors
    plt.rcParams['axes.prop_cycle'] = plt.cycler(color=COLOR_PALETTE)
    plt.rcParams['axes.edgecolor'] = '#333333'
    plt.rcParams['axes.labelcolor'] = '#333333'
    plt.rcParams['text.color'] = '#333333'
    plt.rcParams['xtick.color'] = '#333333'
    plt.rcParams['ytick.color'] = '#333333'

    # Grid - sparse and subtle
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['grid.linestyle'] = '-'
    plt.rcParams['grid.linewidth'] = 0.5
    plt.rcParams['axes.axisbelow'] = True  # Grid behind data

    # Spines - keep them clean
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.right'] = False

    # Figure settings
    plt.rcParams['figure.figsize'] = (10, 6)
    plt.rcParams['figure.dpi'] = 100
    plt.rcParams['savefig.dpi'] = 300
    plt.rcParams['savefig.bbox'] = 'tight'

    # Line widths
    plt.rcParams['lines.linewidth'] = 2
    plt.rcParams['axes.linewidth'] = 1.0

    # Legend
    plt.rcParams['legend.frameon'] = True
    plt.rcParams['legend.framealpha'] = 0.9
    plt.rcParams['legend.edgecolor'] = '#CCCCCC'


def reset_plot_style():
    """Reset matplotlib to default style."""
    mpl.rcParams.update(mpl.rcParamsDefault)


# Convenience function for creating figures with house style
def create_figure(nrows=1, ncols=1, figsize=None, **kwargs):
    """
    Create a figure with house style already applied.

    Args:
        nrows: Number of subplot rows
        ncols: Number of subplot columns
        figsize: Figure size (width, height). If None, uses default from style.
        **kwargs: Additional arguments passed to plt.subplots()

    Returns:
        fig, axes: Figure and axes objects
    """
    apply_plot_style()

    if figsize is None:
        figsize = (10 * ncols, 6 * nrows)

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize, **kwargs)

    return fig, axes
