#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from operator import itemgetter
from typing import Dict, Union, Callable

# 3rd party:
from plotly import graph_objects as go
from pandas import Series

# Internal:
try:
    from constants.website import headline_metrics
except ImportError:
    from __app__.constants.website import headline_metrics

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'plot_thumbnail',
    'get_colour',
]

TIMESERIES_LAYOUT = go.Layout(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    margin={
        'l': 0,
        'r': 0,
        'b': 4,
        't': 0,
    },
    showlegend=False,
    height=350,
    autosize=False,
    xaxis={
        "showgrid": False,
        "zeroline": False,
        "showline": False,
        "ticks": "outside",
        "tickson": "boundaries",
        "type": "date",
        "tickformat": '%b',
        # "tickvals": x[::30],
        # "tickmode": 'array',
        "tickfont": {
            "family": '"GDS Transport", Arial, sans-serif',
            "size": 20,
            "color": "#6B7276"
        }
    }
)

WAFFLE_LAYOUT = dict(
    margin=dict(
        l=22,
        r=0,
        t=20
    ),
    hovermode="x+y",
    height=350,
    legend=dict(
        orientation='v',
        font={
            "family": '"GDS Transport", Arial, sans - serif',
            "size": 16,
        },
        xanchor='center',
        yachor='bottom',
        y=-.3,
        x=.5
    ),
    showlegend=True,
    plot_bgcolor="rgba(231,231,231,0)",
    paper_bgcolor="rgba(255,255,255,0)",
    xaxis=dict(
        showgrid=False,
        ticks=None,
        showticklabels=False
    ),
    yaxis=dict(
        showgrid=False,
        ticks=None,
        showticklabels=False
    ),
)


COLOURS = {
    "good": {
        "line": "rgba(0,90,48,1)",
        "fill": "rgba(204,226,216,1)"
    },
    "bad": {
        "line": "rgba(148,37,20,1)",
        "fill": "rgba(246,215,210,1)"
    },
    "neutral": {
        "line": "rgba(56,63,67,1)",
        "fill": "rgba(235,233,231,1)"
    }
}

IsImproving: Dict[str, Callable[[Union[int, float]], bool]] = {
    "newCasesByPublishDate": lambda x: x < 0,
    "newDeaths28DaysByPublishDate": lambda x: x < 0,
    "newPCRTestsByPublishDate": lambda x: 0,
    "newAdmissions": lambda x: x < 0,
}


def get_colour(change, metric_name):
    change_value = float(change["value"])
    improving = IsImproving[metric_name](change_value)

    trend_colour = COLOURS["neutral"]

    if improving != 0 and change_value != 0:
        if improving:
            trend_colour = COLOURS["good"]
        else:
            trend_colour = COLOURS["bad"]

    return trend_colour


def plot_thumbnail(timeseries, change, metric_name):
    get_date = itemgetter("date")
    get_value = itemgetter("value")

    trend_colour = get_colour(change, metric_name)

    x = list(map(get_date, timeseries))
    y = Series(list(map(get_value, timeseries))).rolling(7, center=True).mean()
    fig = go.Figure(
        go.Scatter(
            x=x[13:],
            y=y[13:],
            line={
                "width": 2,
                "color": COLOURS['neutral']['line']
            }
        ),
        layout=TIMESERIES_LAYOUT
    )

    fig.add_trace(
        go.Scatter(
            x=x[:14],
            y=y[:14],
            line={
                "width": 2
            },
            mode='lines',
            fill='tozeroy',
            hoveron='points',
            opacity=.5,
            line_color=trend_colour['line'],
            fillcolor=trend_colour['fill'],
        )
    )

    fig.update_yaxes(showticklabels=False)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)

    return fig.to_image(format="svg", height='150px').decode()

