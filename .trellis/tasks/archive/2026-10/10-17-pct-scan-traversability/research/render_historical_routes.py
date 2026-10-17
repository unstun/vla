"""Render returned historical geometry with ReportLab's standard XY plots."""
from pathlib import Path
import sys
import numpy as np
from reportlab.graphics.shapes import Drawing, String, Circle
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib import colors

folder = Path(sys.argv[1])
data = np.load(folder/'plot_data.npz', allow_pickle=False)
drawing = Drawing(900, 450)
drawing.add(String(450, 430, 'Archived stair-region routes: initial PCT reference is identical', textAnchor='middle', fontSize=14))
keys = ('initial', 'active45', 'active50', 'body')
palette = (colors.HexColor('#999999'), colors.HexColor('#0066cc'), colors.HexColor('#cc6600'), colors.HexColor('#bb2244'))
for i, version in enumerate(('v210', 'v219')):
    chart = LinePlot()
    chart.x = 55+i*445;chart.y = 60;chart.width = 350;chart.height = 350/2.1*2.
    chart.xValueAxis.valueMin = 6.7;chart.xValueAxis.valueMax = 8.8
    chart.yValueAxis.valueMin = -4.8;chart.yValueAxis.valueMax = -2.8
    chart.xValueAxis.valueStep = .5;chart.yValueAxis.valueStep = .5
    chart.xValueAxis.labels.fontSize = chart.yValueAxis.labels.fontSize = 8
    chart.xValueAxis.labelTextFormat = '%.1f';chart.yValueAxis.labelTextFormat = '%.1f'
    datasets = []
    for key in keys:
        points = data[f'{version}_{key}']
        xy = points[:, 1:3] if key == 'body' else points[:, :2]
        # Restrict the entire polyline to the displayed window.
        xy = xy[(xy[:, 0]>=6.7)&(xy[:, 0]<=8.8)&(xy[:, 1]>=-4.8)&(xy[:, 1]<=-2.8)]
        datasets.append([tuple(p) for p in xy])
    chart.data = datasets
    for j, color in enumerate(palette):
        chart.lines[j].strokeColor = color;chart.lines[j].strokeWidth = 1.4
    surface = data['surface']
    for x,y,z,_ in surface:
        if 6.7<=x<=8.8 and -4.8<=y<=-2.8:
            drawing.add(Circle(chart.x+(x-6.7)/2.1*chart.width, chart.y+(y+4.8)/2.*chart.height,
                               .6, fillColor=colors.HexColor('#dddddd'), strokeColor=None))
    drawing.add(chart)
    drawing.add(String(chart.x+175, 410, version, textAnchor='middle', fontSize=13))
    drawing.add(String(chart.x+175, 35, 'World x (m)', textAnchor='middle', fontSize=10))
for j,(color,label) in enumerate(zip(palette, ('Initial reference', 'Reference at 45 s', 'Reference at 50 s', 'Robot body, 45-55 s'))):
    drawing.add(String(50+j*220, 12, label, fillColor=color, fontSize=10))
renderSVG.drawToFile(drawing, str(folder/'historical_routes.svg'))
