/**
 * Draw.io Flowchart Generator
 * Creates professional flowcharts in draw.io XML format
 *
 * Key principles (from draw-io skill):
 * - Edges MUST be defined BEFORE vertices (Z-order)
 * - fontFamily="Arial" on ALL elements
 * - Proper arrow layering
 */

const fs = require('fs');
const logger = require('../utils/logger');

class FlowchartDrawioGenerator {
  constructor() {
    this.nodeTypes = {
      start: { style: 'ellipse', fill: '#D5E8D4', stroke: '#82B366' },
      end: { style: 'ellipse', fill: '#D5E8D4', stroke: '#82B366' },
      process: { style: 'rounded=1', fill: '#DAE8FC', stroke: '#6C8EBF' },
      decision: { style: 'rhombus', fill: '#FFF2CC', stroke: '#D6B656' },
      api: { style: 'rounded=1', fill: '#E1D5E7', stroke: '#9673A6' },
      queue: { style: 'rounded=1', fill: '#D5E8FC', stroke: '#6C8EBF' },
      disconnect: { style: 'ellipse', fill: '#F8CECC', stroke: '#B85450' },
      timer: { style: 'rounded=1', fill: '#FFE6CC', stroke: '#D79B00' },
      sms: { style: 'rounded=1', fill: '#E6FFE6', stroke: '#66B366' }
    };

    this.defaultNodeSize = { width: 120, height: 60 };
    this.decisionSize = { width: 100, height: 80 };
  }

  /**
   * Generate draw.io XML from flowchart structure
   */
  generate(flowchartData, outputPath) {
    const { title, nodes, edges } = flowchartData;

    // Calculate node positions (simple auto-layout)
    const positionedNodes = this.autoLayout(nodes, edges);

    // Build XML - EDGES FIRST (critical for Z-order)
    const edgesXml = edges.map(edge => this.createEdgeXml(edge)).join('\n');
    const nodesXml = positionedNodes.map(node => this.createNodeXml(node)).join('\n');
    const legendXml = this.createLegendXml(title);

    const xml = this.wrapInDocument(title, edgesXml + '\n' + nodesXml + '\n' + legendXml);

    fs.writeFileSync(outputPath, xml);
    logger.info(`Flowchart generated: ${outputPath}`);
    return outputPath;
  }

  /**
   * Simple auto-layout algorithm
   */
  autoLayout(nodes, edges) {
    const positioned = [];
    const levels = this.calculateLevels(nodes, edges);
    const nodesPerLevel = {};

    // Group nodes by level
    nodes.forEach(node => {
      const level = levels[node.id] || 0;
      if (!nodesPerLevel[level]) nodesPerLevel[level] = [];
      nodesPerLevel[level].push(node);
    });

    // Position nodes
    const xSpacing = 180;
    const ySpacing = 120;
    const startX = 80;
    const startY = 60;

    Object.keys(nodesPerLevel).sort((a, b) => a - b).forEach(level => {
      const levelNodes = nodesPerLevel[level];
      levelNodes.forEach((node, index) => {
        const nodeType = this.nodeTypes[node.type] || this.nodeTypes.process;
        const size = node.type === 'decision' ? this.decisionSize : this.defaultNodeSize;

        positioned.push({
          ...node,
          x: startX + (index * xSpacing * 1.5),
          y: startY + (parseInt(level) * ySpacing),
          width: size.width,
          height: size.height,
          ...nodeType
        });
      });
    });

    return positioned;
  }

  /**
   * Calculate levels for nodes (BFS from start)
   */
  calculateLevels(nodes, edges) {
    const levels = {};
    const adjacency = {};

    // Build adjacency list
    edges.forEach(edge => {
      if (!adjacency[edge.from]) adjacency[edge.from] = [];
      adjacency[edge.from].push(edge.to);
    });

    // Find start node
    const startNode = nodes.find(n => n.type === 'start') || nodes[0];
    const queue = [{ id: startNode.id, level: 0 }];
    const visited = new Set();

    while (queue.length > 0) {
      const { id, level } = queue.shift();
      if (visited.has(id)) continue;
      visited.add(id);
      levels[id] = level;

      const neighbors = adjacency[id] || [];
      neighbors.forEach(neighborId => {
        if (!visited.has(neighborId)) {
          queue.push({ id: neighborId, level: level + 1 });
        }
      });
    }

    // Handle disconnected nodes
    nodes.forEach(node => {
      if (levels[node.id] === undefined) {
        levels[node.id] = Object.keys(levels).length;
      }
    });

    return levels;
  }

  /**
   * Create XML for an edge
   */
  createEdgeXml(edge) {
    const edgeColor = edge.color || '#333333';
    const labelColor = edge.label?.toLowerCase().includes('no') ? '#CC4444' :
                       edge.label?.toLowerCase().includes('yes') ? '#22AA22' : '#333333';

    let xml = `        <mxCell id="e_${edge.from}_${edge.to}" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;strokeColor=${edgeColor};fontFamily=Arial;" edge="1" parent="1" source="${edge.from}" target="${edge.to}">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>`;

    if (edge.label) {
      xml += `
        <mxCell id="e_${edge.from}_${edge.to}_label" value="${edge.label}" style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontFamily=Arial;fontSize=11;fontColor=${labelColor};" vertex="1" connectable="0" parent="e_${edge.from}_${edge.to}">
          <mxGeometry x="-0.3" relative="1" as="geometry">
            <mxPoint as="offset"/>
          </mxGeometry>
        </mxCell>`;
    }

    return xml;
  }

  /**
   * Create XML for a node
   */
  createNodeXml(node) {
    const label = node.sublabel ? `${node.label}&#xa;${node.sublabel}` : node.label;
    const fontStyle = node.type === 'start' || node.type === 'end' || node.type === 'decision' ? 'fontStyle=1;' : '';

    return `        <mxCell id="${node.id}" value="${label}" style="${node.style};whiteSpace=wrap;html=1;fillColor=${node.fill};strokeColor=${node.stroke};strokeWidth=2;fontFamily=Arial;fontSize=12;${fontStyle}" vertex="1" parent="1">
          <mxGeometry x="${node.x}" y="${node.y}" width="${node.width}" height="${node.height}" as="geometry"/>
        </mxCell>`;
  }

  /**
   * Create legend XML
   */
  createLegendXml(title) {
    const legendX = 720;
    const legendY = 40;

    return `
        <!-- Title -->
        <mxCell id="title" value="${title}" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontFamily=Arial;fontSize=16;fontStyle=1;fontColor=#1F4E79;" vertex="1" parent="1">
          <mxGeometry x="${legendX}" y="${legendY}" width="300" height="40" as="geometry"/>
        </mxCell>

        <!-- Legend Box -->
        <mxCell id="legend_box" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#CCCCCC;strokeWidth=1;" vertex="1" parent="1">
          <mxGeometry x="${legendX}" y="${legendY + 50}" width="200" height="160" as="geometry"/>
        </mxCell>

        <mxCell id="legend_title" value="Legend" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;rounded=0;fontFamily=Arial;fontSize=13;fontStyle=1;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 20}" y="${legendY + 60}" width="100" height="20" as="geometry"/>
        </mxCell>

        <mxCell id="leg1" value="" style="ellipse;whiteSpace=wrap;html=1;fillColor=#D5E8D4;strokeColor=#82B366;strokeWidth=1;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 20}" y="${legendY + 85}" width="16" height="16" as="geometry"/>
        </mxCell>
        <mxCell id="leg1_text" value="Start / End" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontFamily=Arial;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 45}" y="${legendY + 85}" width="100" height="16" as="geometry"/>
        </mxCell>

        <mxCell id="leg2" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#DAE8FC;strokeColor=#6C8EBF;strokeWidth=1;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 20}" y="${legendY + 105}" width="16" height="16" as="geometry"/>
        </mxCell>
        <mxCell id="leg2_text" value="Process" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontFamily=Arial;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 45}" y="${legendY + 105}" width="100" height="16" as="geometry"/>
        </mxCell>

        <mxCell id="leg3" value="" style="rhombus;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D6B656;strokeWidth=1;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 20}" y="${legendY + 125}" width="16" height="16" as="geometry"/>
        </mxCell>
        <mxCell id="leg3_text" value="Decision" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontFamily=Arial;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 45}" y="${legendY + 125}" width="100" height="16" as="geometry"/>
        </mxCell>

        <mxCell id="leg4" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E1D5E7;strokeColor=#9673A6;strokeWidth=1;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 20}" y="${legendY + 145}" width="16" height="16" as="geometry"/>
        </mxCell>
        <mxCell id="leg4_text" value="API / Integration" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontFamily=Arial;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 45}" y="${legendY + 145}" width="100" height="16" as="geometry"/>
        </mxCell>

        <mxCell id="leg5" value="" style="ellipse;whiteSpace=wrap;html=1;fillColor=#F8CECC;strokeColor=#B85450;strokeWidth=1;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 20}" y="${legendY + 165}" width="16" height="16" as="geometry"/>
        </mxCell>
        <mxCell id="leg5_text" value="Disconnect / Error" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontFamily=Arial;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="${legendX + 45}" y="${legendY + 165}" width="100" height="16" as="geometry"/>
        </mxCell>`;
  }

  /**
   * Wrap content in draw.io document structure
   */
  wrapInDocument(title, content) {
    const timestamp = new Date().toISOString();
    const diagramId = title.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');

    return `<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="app.diagrams.net" modified="${timestamp}" version="21.0.0" type="device">
  <diagram id="${diagramId}" name="${title}">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1100" pageHeight="850" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>

${content}

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>`;
  }
}

module.exports = FlowchartDrawioGenerator;
