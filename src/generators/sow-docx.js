/**
 * SOW Document Generator
 * Creates professional Word documents from structured SOW data
 */

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat
} = require('docx');
const fs = require('fs');
const path = require('path');
const logger = require('../utils/logger');

class SowDocxGenerator {
  constructor() {
    this.border = { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' };
    this.borders = {
      top: this.border,
      bottom: this.border,
      left: this.border,
      right: this.border
    };
    this.headerBorder = { style: BorderStyle.SINGLE, size: 2, color: '1F4E79' };
    this.headerBorders = {
      top: this.headerBorder,
      bottom: this.headerBorder,
      left: this.headerBorder,
      right: this.headerBorder
    };
  }

  /**
   * Generate SOW document from structured data
   */
  async generate(sowData, outputPath) {
    const doc = new Document({
      styles: this.getStyles(),
      numbering: this.getNumberingConfig(),
      sections: [{
        properties: this.getPageProperties(),
        headers: { default: this.createHeader(sowData) },
        footers: { default: this.createFooter() },
        children: this.buildContent(sowData)
      }]
    });

    const buffer = await Packer.toBuffer(doc);
    fs.writeFileSync(outputPath, buffer);
    logger.info(`SOW document generated: ${outputPath}`);
    return outputPath;
  }

  getStyles() {
    return {
      default: { document: { run: { font: 'Arial', size: 22 } } },
      paragraphStyles: [
        {
          id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal',
          quickFormat: true,
          run: { size: 32, bold: true, font: 'Arial', color: '1F4E79' },
          paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 }
        },
        {
          id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal',
          quickFormat: true,
          run: { size: 26, bold: true, font: 'Arial', color: '2E75B6' },
          paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 1 }
        }
      ]
    };
  }

  getNumberingConfig() {
    return {
      config: [
        {
          reference: 'bullets',
          levels: [{
            level: 0, format: LevelFormat.BULLET, text: '•',
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } }
          }]
        },
        {
          reference: 'numbers',
          levels: [{
            level: 0, format: LevelFormat.DECIMAL, text: '%1.',
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } }
          }]
        }
      ]
    };
  }

  getPageProperties() {
    return {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    };
  }

  createHeader(sowData) {
    return new Header({
      children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        children: [
          new TextRun({ text: 'Statement of Work | ', font: 'Arial', size: 20, color: '666666' }),
          new TextRun({ text: sowData.customer, font: 'Arial', size: 20, bold: true, color: '1F4E79' })
        ]
      })]
    });
  }

  createFooter() {
    return new Footer({
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [
          new TextRun({ text: 'Confidential | Exotel Techcom Pvt. Ltd. | Page ', font: 'Arial', size: 18, color: '666666' }),
          new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 18, color: '666666' })
        ]
      })]
    });
  }

  buildContent(sowData) {
    const content = [];

    // Title
    content.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 400 },
        children: [new TextRun({ text: 'STATEMENT OF WORK', bold: true, font: 'Arial', size: 48, color: '1F4E79' })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 600 },
        children: [new TextRun({ text: sowData.project, font: 'Arial', size: 32, color: '2E75B6' })]
      })
    );

    // Project Info Table
    content.push(this.createProjectInfoTable(sowData));
    content.push(new Paragraph({ children: [new PageBreak()] }));

    // Business Goals
    content.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('1. Business Goals')] }));
    if (sowData.businessGoals) {
      sowData.businessGoals.forEach(goal => {
        content.push(new Paragraph({
          numbering: { reference: 'bullets', level: 0 },
          children: [new TextRun({ text: goal, font: 'Arial', size: 22 })]
        }));
      });
    }
    content.push(new Paragraph({ spacing: { after: 300 }, children: [] }));

    // Prerequisites
    content.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('2. Prerequisites')] }));
    if (sowData.prerequisites && sowData.prerequisites.length > 0) {
      content.push(this.createPrerequisitesTable(sowData.prerequisites));
    }
    content.push(new Paragraph({ spacing: { after: 300 }, children: [] }));

    // Scope of Work / Modules
    content.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('3. Scope of Work / Deliverables')] }));
    if (sowData.modules) {
      sowData.modules.forEach((module, index) => {
        content.push(
          new Paragraph({
            heading: HeadingLevel.HEADING_2,
            children: [new TextRun(`3.${index + 1} ${module.name} (${module.id})`)]
          }),
          this.createModuleTable(module),
          new Paragraph({ spacing: { after: 200 }, children: [] })
        );
      });
    }

    // Timeline
    content.push(new Paragraph({ children: [new PageBreak()] }));
    content.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('4. Deployment Plan')] }));
    if (sowData.timeline) {
      content.push(this.createTimelineTable(sowData.timeline, sowData.totalDuration));
    }
    content.push(new Paragraph({ spacing: { after: 300 }, children: [] }));

    // Notes
    content.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('5. Notes')] }));
    if (sowData.notes) {
      sowData.notes.forEach(note => {
        content.push(new Paragraph({
          numbering: { reference: 'bullets', level: 0 },
          children: [new TextRun({ text: note, font: 'Arial', size: 22 })]
        }));
      });
    }
    content.push(new Paragraph({ spacing: { after: 300 }, children: [] }));

    // Assumptions
    content.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('6. Assumptions')] }));
    if (sowData.assumptions) {
      sowData.assumptions.forEach(assumption => {
        content.push(new Paragraph({
          numbering: { reference: 'bullets', level: 0 },
          children: [new TextRun({ text: assumption, font: 'Arial', size: 22 })]
        }));
      });
    }
    content.push(new Paragraph({ spacing: { after: 300 }, children: [] }));

    // Escalation Matrix
    content.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('7. Escalation Matrix')] }));
    if (sowData.escalationMatrix) {
      content.push(this.createEscalationTable(sowData.escalationMatrix));
    }
    content.push(new Paragraph({ spacing: { after: 400 }, children: [] }));

    // Acceptance Section
    content.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('8. Acceptance')] }));
    content.push(new Paragraph({
      spacing: { after: 300 },
      children: [new TextRun({ text: 'By signing below, both parties agree to the scope, deliverables, and terms outlined in this Statement of Work.', font: 'Arial', size: 22 })]
    }));
    content.push(this.createSignatureTable(sowData));

    return content;
  }

  createHeaderCell(text, width) {
    return new TableCell({
      borders: this.headerBorders,
      width: { size: width, type: WidthType.DXA },
      shading: { fill: '1F4E79', type: ShadingType.CLEAR },
      margins: { top: 100, bottom: 100, left: 120, right: 120 },
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text, bold: true, color: 'FFFFFF', font: 'Arial', size: 22 })]
      })]
    });
  }

  createCell(text, width, options = {}) {
    return new TableCell({
      borders: this.borders,
      width: { size: width, type: WidthType.DXA },
      shading: options.shading ? { fill: options.shading, type: ShadingType.CLEAR } : undefined,
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({
        alignment: options.align || AlignmentType.LEFT,
        children: [new TextRun({
          text: text || '',
          bold: options.bold || false,
          font: 'Arial',
          size: 22
        })]
      })]
    });
  }

  createProjectInfoTable(sowData) {
    const rows = [
      ['Customer', sowData.customer],
      ['Project Name', sowData.project],
      ['Document Version', sowData.version || '1.0.0'],
      ['Date', sowData.date || new Date().toISOString().split('T')[0]],
      ['Prepared By', sowData.preparedBy || 'Exotel PS Team']
    ];

    return new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [3120, 6240],
      rows: rows.map(([label, value]) => new TableRow({
        children: [
          this.createCell(label, 3120, { bold: true, shading: 'F2F2F2' }),
          this.createCell(value, 6240)
        ]
      }))
    });
  }

  createPrerequisitesTable(prerequisites) {
    return new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [600, 5760, 3000],
      rows: [
        new TableRow({
          children: [
            this.createHeaderCell('#', 600),
            this.createHeaderCell('Prerequisite', 5760),
            this.createHeaderCell('Status', 3000)
          ]
        }),
        ...prerequisites.map((prereq, i) => new TableRow({
          children: [
            this.createCell(String(i + 1), 600, { align: AlignmentType.CENTER }),
            this.createCell(prereq.item, 5760),
            this.createCell(prereq.status || 'Required', 3000, { align: AlignmentType.CENTER })
          ]
        }))
      ]
    });
  }

  createModuleTable(module) {
    const rows = [
      ['Module ID', module.id],
      ['Description', module.description],
      ['Configuration', module.configuration || 'Standard configuration']
    ];

    if (module.dependencies && module.dependencies.length > 0) {
      rows.push(['Dependencies', module.dependencies.join(', ')]);
    }

    return new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [2400, 6960],
      rows: rows.map(([label, value]) => new TableRow({
        children: [
          this.createCell(label, 2400, { bold: true, shading: 'F2F2F2' }),
          this.createCell(value, 6960)
        ]
      }))
    });
  }

  createTimelineTable(timeline, totalDuration) {
    const rows = [
      new TableRow({
        children: [
          this.createHeaderCell('#', 600),
          this.createHeaderCell('Phase', 3000),
          this.createHeaderCell('Activities', 3360),
          this.createHeaderCell('Duration', 2400)
        ]
      }),
      ...timeline.map((phase, i) => new TableRow({
        children: [
          this.createCell(String(i + 1), 600, { align: AlignmentType.CENTER }),
          this.createCell(phase.phase, 3000),
          this.createCell(phase.activities, 3360),
          this.createCell(phase.duration, 2400, { align: AlignmentType.CENTER })
        ]
      }))
    ];

    if (totalDuration) {
      rows.push(new TableRow({
        children: [
          this.createCell('', 600),
          this.createCell('Total Estimated Duration', 3000, { bold: true, shading: 'F2F2F2' }),
          this.createCell('', 3360),
          this.createCell(totalDuration, 2400, { bold: true, align: AlignmentType.CENTER, shading: 'F2F2F2' })
        ]
      }));
    }

    return new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [600, 3000, 3360, 2400],
      rows
    });
  }

  createEscalationTable(escalationMatrix) {
    return new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [2340, 2340, 2340, 2340],
      rows: [
        new TableRow({
          children: [
            this.createHeaderCell('Level', 2340),
            this.createHeaderCell('Contact', 2340),
            this.createHeaderCell('Role', 2340),
            this.createHeaderCell('Response Time', 2340)
          ]
        }),
        ...escalationMatrix.map(row => new TableRow({
          children: [
            this.createCell(row.level, 2340),
            this.createCell(row.contact, 2340),
            this.createCell(row.role, 2340),
            this.createCell(row.responseTime, 2340)
          ]
        }))
      ]
    });
  }

  createSignatureTable(sowData) {
    return new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [4680, 4680],
      rows: [
        new TableRow({
          children: [
            this.createHeaderCell('Exotel Techcom Pvt. Ltd.', 4680),
            this.createHeaderCell(sowData.customer, 4680)
          ]
        }),
        new TableRow({
          children: [
            this.createCell('Authorized Signature: _________________', 4680),
            this.createCell('Authorized Signature: _________________', 4680)
          ]
        }),
        new TableRow({
          children: [
            this.createCell('Name: _________________', 4680),
            this.createCell('Name: _________________', 4680)
          ]
        }),
        new TableRow({
          children: [
            this.createCell('Date: _________________', 4680),
            this.createCell('Date: _________________', 4680)
          ]
        })
      ]
    });
  }
}

module.exports = SowDocxGenerator;
