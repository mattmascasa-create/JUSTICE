import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { format } from 'date-fns';
import QRCode from 'qrcode';

// Helper to generate QR code as data URL
async function generateQRCode(text, size = 100) {
  try {
    return await QRCode.toDataURL(text, {
      width: size,
      margin: 1,
      color: { dark: '#000000', light: '#ffffff' }
    });
  } catch (err) {
    console.error('QR code generation error:', err);
    return null;
  }
}

export async function generateCaseReport(reportData) {
  const { case: caseData, evidence, timeline, user, generated_at, report_id } = reportData;
  
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 20;
  let yPos = 20;

  // Helper function to add text with word wrap
  const addText = (text, x, y, maxWidth, fontSize = 10) => {
    doc.setFontSize(fontSize);
    const lines = doc.splitTextToSize(text, maxWidth);
    doc.text(lines, x, y);
    return y + (lines.length * fontSize * 0.4);
  };

  // Header
  doc.setFillColor(15, 23, 42); // Dark blue
  doc.rect(0, 0, pageWidth, 40, 'F');
  
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(24);
  doc.setFont('helvetica', 'bold');
  doc.text('JUSTICE', margin, 25);
  
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text('Constitutional Rights Protection Platform', margin, 33);
  
  doc.setFontSize(8);
  doc.text(`Report ID: ${report_id}`, pageWidth - margin - 50, 25);
  doc.text(`Generated: ${format(new Date(generated_at), 'MMM dd, yyyy HH:mm')}`, pageWidth - margin - 50, 33);

  yPos = 55;
  doc.setTextColor(0, 0, 0);

  // Case Title Section
  doc.setFillColor(248, 250, 252);
  doc.rect(margin, yPos - 5, pageWidth - 2 * margin, 25, 'F');
  
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('CASE REPORT', margin + 5, yPos + 5);
  
  doc.setFontSize(12);
  doc.setFont('helvetica', 'normal');
  yPos = addText(caseData.title, margin + 5, yPos + 15, pageWidth - 2 * margin - 10, 12);
  
  yPos += 15;

  // Case Details
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text('Case Details', margin, yPos);
  yPos += 8;

  const caseDetails = [
    ['Case ID', caseData.case_id],
    ['Status', caseData.status.toUpperCase()],
    ['Severity', caseData.severity.toUpperCase()],
    ['Violation Type', caseData.violation_type],
    ['Incident Date', format(new Date(caseData.incident_date), 'MMMM dd, yyyy')],
    ['Location', caseData.location],
    ['Department', caseData.department || 'Not specified'],
    ['Officer Name', caseData.officer_name || 'Not specified'],
    ['Officer Badge', caseData.officer_badge || 'Not specified'],
    ['Created', format(new Date(caseData.created_at), 'MMM dd, yyyy HH:mm')],
    ['Last Updated', format(new Date(caseData.updated_at), 'MMM dd, yyyy HH:mm')],
  ];

  autoTable(doc, {
    startY: yPos,
    head: [],
    body: caseDetails,
    theme: 'plain',
    styles: { fontSize: 9, cellPadding: 3 },
    columnStyles: {
      0: { fontStyle: 'bold', cellWidth: 40 },
      1: { cellWidth: 100 }
    },
    margin: { left: margin, right: margin }
  });

  yPos = doc.lastAutoTable.finalY + 15;

  // Description
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text('Incident Description', margin, yPos);
  yPos += 8;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  yPos = addText(caseData.description, margin, yPos, pageWidth - 2 * margin, 9);
  yPos += 10;

  // Check if we need a new page
  if (yPos > 250) {
    doc.addPage();
    yPos = 20;
  }

  // Evidence Section
  if (evidence && evidence.length > 0) {
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text(`Evidence (${evidence.length} files)`, margin, yPos);
    yPos += 8;

    const evidenceData = evidence.map((ev, index) => [
      index + 1,
      ev.file_name,
      ev.file_type,
      `${(ev.file_size / 1024).toFixed(1)} KB`,
      format(new Date(ev.uploaded_at), 'MMM dd, yyyy'),
      ev.blockchain_hash ? '✓ Verified' : 'Pending'
    ]);

    autoTable(doc, {
      startY: yPos,
      head: [['#', 'File Name', 'Type', 'Size', 'Uploaded', 'Blockchain']],
      body: evidenceData,
      theme: 'striped',
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [59, 130, 246], textColor: 255 },
      margin: { left: margin, right: margin }
    });

    yPos = doc.lastAutoTable.finalY + 15;
  }

  // Check if we need a new page
  if (yPos > 250) {
    doc.addPage();
    yPos = 20;
  }

  // Timeline Section
  if (timeline && timeline.length > 0) {
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text('Case Timeline', margin, yPos);
    yPos += 8;

    const timelineData = timeline.map(event => [
      format(new Date(event.created_at), 'MMM dd, yyyy HH:mm'),
      event.event_type.replace('_', ' ').toUpperCase(),
      event.description
    ]);

    autoTable(doc, {
      startY: yPos,
      head: [['Date/Time', 'Event', 'Description']],
      body: timelineData,
      theme: 'striped',
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [59, 130, 246], textColor: 255 },
      columnStyles: {
        0: { cellWidth: 35 },
        1: { cellWidth: 30 },
        2: { cellWidth: 85 }
      },
      margin: { left: margin, right: margin }
    });

    yPos = doc.lastAutoTable.finalY + 15;
  }

  // Footer on last page
  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(128, 128, 128);
    doc.text(
      `Page ${i} of ${pageCount} | JUSTICE Platform | Confidential Case Report`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 10,
      { align: 'center' }
    );
  }

  // Disclaimer
  doc.setPage(pageCount);
  yPos = doc.internal.pageSize.getHeight() - 30;
  doc.setFillColor(254, 243, 199);
  doc.rect(margin, yPos - 5, pageWidth - 2 * margin, 15, 'F');
  doc.setTextColor(146, 64, 14);
  doc.setFontSize(7);
  doc.text(
    'DISCLAIMER: This report is generated for informational purposes. It does not constitute legal advice. Consult a licensed attorney for legal matters.',
    margin + 5,
    yPos + 3
  );

  return doc;
}

export function downloadCaseReport(doc, caseId) {
  doc.save(`JUSTICE_Case_Report_${caseId}.pdf`);
}

export function openCaseReportInNewTab(doc) {
  const pdfBlob = doc.output('blob');
  const pdfUrl = URL.createObjectURL(pdfBlob);
  window.open(pdfUrl, '_blank');
}

/**
 * Generate a comprehensive Evidence Report PDF with IPFS verification
 */
export async function generateEvidenceReport(reportData) {
  const { 
    report_id, 
    generated_at, 
    case: caseData, 
    evidence_summary, 
    evidence, 
    ipfs_status, 
    blockchain_status,
    verification_instructions,
    legal_notice
  } = reportData;
  
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 15;
  let yPos = 15;

  // Helper function
  const addText = (text, x, y, maxWidth, fontSize = 10) => {
    doc.setFontSize(fontSize);
    const lines = doc.splitTextToSize(text || '', maxWidth);
    doc.text(lines, x, y);
    return y + (lines.length * fontSize * 0.4);
  };

  const checkNewPage = () => {
    if (yPos > 260) {
      doc.addPage();
      yPos = 20;
    }
  };

  // ===== HEADER =====
  doc.setFillColor(15, 23, 42);
  doc.rect(0, 0, pageWidth, 35, 'F');
  
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(20);
  doc.setFont('helvetica', 'bold');
  doc.text('JUSTICE', margin, 20);
  
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text('Evidence Verification Report', margin, 28);
  
  doc.setFontSize(7);
  doc.text(`Report: ${report_id}`, pageWidth - margin - 45, 20);
  doc.text(`Generated: ${format(new Date(generated_at), 'MMM dd, yyyy HH:mm')}`, pageWidth - margin - 45, 26);

  yPos = 45;
  doc.setTextColor(0, 0, 0);

  // ===== STORAGE STATUS BANNER =====
  const ipfsActive = ipfs_status.total_files_on_ipfs > 0;
  doc.setFillColor(ipfsActive ? 34 : 245, ipfsActive ? 197 : 158, ipfsActive ? 94 : 11);
  doc.rect(margin, yPos - 5, pageWidth - 2 * margin, 18, 'F');
  
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text(ipfsActive ? 'DECENTRALIZED STORAGE ACTIVE' : 'LOCAL STORAGE ONLY', margin + 5, yPos + 3);
  
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.text(
    ipfsActive 
      ? `${ipfs_status.total_files_on_ipfs} files stored on IPFS | ${blockchain_status.total_verified} blockchain verified`
      : 'IPFS not configured - evidence stored locally',
    margin + 5, 
    yPos + 10
  );
  
  yPos += 22;
  doc.setTextColor(0, 0, 0);

  // ===== CASE INFORMATION =====
  doc.setFillColor(248, 250, 252);
  doc.rect(margin, yPos, pageWidth - 2 * margin, 8, 'F');
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('CASE INFORMATION', margin + 3, yPos + 6);
  yPos += 12;

  const caseDetails = [
    ['Case ID', caseData.case_id],
    ['Title', caseData.title],
    ['Status', (caseData.status || '').toUpperCase()],
    ['Severity', (caseData.severity || '').toUpperCase()],
    ['Violation', caseData.violation_type],
    ['Incident Date', caseData.incident_date ? format(new Date(caseData.incident_date), 'MMMM dd, yyyy') : 'N/A'],
    ['Location', caseData.location || 'N/A'],
    ['Department', caseData.department || 'N/A'],
    ['Officer', caseData.officer_name || 'N/A'],
    ['Badge #', caseData.officer_badge || 'N/A'],
  ];

  autoTable(doc, {
    startY: yPos,
    body: caseDetails,
    theme: 'plain',
    styles: { fontSize: 8, cellPadding: 2 },
    columnStyles: { 0: { fontStyle: 'bold', cellWidth: 30 }, 1: { cellWidth: 80 } },
    margin: { left: margin }
  });
  yPos = doc.lastAutoTable.finalY + 10;

  checkNewPage();

  // ===== EVIDENCE SUMMARY =====
  doc.setFillColor(248, 250, 252);
  doc.rect(margin, yPos, pageWidth - 2 * margin, 8, 'F');
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('EVIDENCE SUMMARY', margin + 3, yPos + 6);
  yPos += 12;

  const summaryData = [
    ['Total Evidence Files', evidence_summary.total_files.toString()],
    ['Blockchain Verified', evidence_summary.blockchain_verified.toString()],
    ['IPFS Stored', evidence_summary.ipfs_stored.toString()],
    ['Documents', evidence_summary.types.document.toString()],
    ['Images', evidence_summary.types.image.toString()],
    ['Videos', evidence_summary.types.video.toString()],
    ['Audio Files', evidence_summary.types.audio.toString()],
  ];

  autoTable(doc, {
    startY: yPos,
    body: summaryData,
    theme: 'plain',
    styles: { fontSize: 8, cellPadding: 2 },
    columnStyles: { 0: { fontStyle: 'bold', cellWidth: 40 }, 1: { cellWidth: 30 } },
    margin: { left: margin }
  });
  yPos = doc.lastAutoTable.finalY + 10;

  checkNewPage();

  // ===== EVIDENCE DETAILS =====
  if (evidence && evidence.length > 0) {
    doc.setFillColor(248, 250, 252);
    doc.rect(margin, yPos, pageWidth - 2 * margin, 8, 'F');
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.text('EVIDENCE DETAILS', margin + 3, yPos + 6);
    yPos += 12;

    for (let i = 0; i < evidence.length; i++) {
      const ev = evidence[i];
      checkNewPage();

      // Evidence item header
      doc.setFillColor(59, 130, 246);
      doc.rect(margin, yPos, pageWidth - 2 * margin, 7, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(9);
      doc.setFont('helvetica', 'bold');
      doc.text(`Evidence #${i + 1}: ${ev.file_name}`, margin + 3, yPos + 5);
      yPos += 10;
      doc.setTextColor(0, 0, 0);

      // Basic info
      const basicInfo = [
        ['Evidence ID', ev.evidence_id],
        ['File Type', ev.file_type || 'document'],
        ['File Size', ev.file_size ? `${(ev.file_size / 1024).toFixed(1)} KB` : 'N/A'],
        ['Uploaded', ev.uploaded_at ? format(new Date(ev.uploaded_at), 'MMM dd, yyyy HH:mm') : 'N/A'],
        ['Description', ev.description || 'N/A'],
      ];

      autoTable(doc, {
        startY: yPos,
        body: basicInfo,
        theme: 'plain',
        styles: { fontSize: 7, cellPadding: 1 },
        columnStyles: { 0: { fontStyle: 'bold', cellWidth: 25 }, 1: { cellWidth: 90 } },
        margin: { left: margin }
      });
      yPos = doc.lastAutoTable.finalY + 3;

      // Cryptographic verification
      if (ev.hash_record) {
        doc.setFontSize(8);
        doc.setFont('helvetica', 'bold');
        doc.text('Cryptographic Hashes (SHA-256):', margin, yPos + 3);
        yPos += 6;

        const hashData = [
          ['File Hash', ev.hash_record.file_hash || 'N/A'],
          ['Metadata Hash', ev.hash_record.metadata_hash || 'N/A'],
          ['Combined Hash', ev.hash_record.combined_hash || 'N/A'],
        ];

        autoTable(doc, {
          startY: yPos,
          body: hashData,
          theme: 'plain',
          styles: { fontSize: 6, cellPadding: 1, font: 'courier' },
          columnStyles: { 0: { fontStyle: 'bold', cellWidth: 28, font: 'helvetica' }, 1: { cellWidth: 100 } },
          margin: { left: margin }
        });
        yPos = doc.lastAutoTable.finalY + 3;
      }

      // IPFS info
      if (ev.ipfs_cid) {
        doc.setFillColor(34, 197, 94);
        doc.rect(margin, yPos, pageWidth - 2 * margin, 12, 'F');
        doc.setTextColor(255, 255, 255);
        doc.setFontSize(7);
        doc.setFont('helvetica', 'bold');
        doc.text('IPFS DECENTRALIZED STORAGE', margin + 3, yPos + 4);
        doc.setFont('helvetica', 'normal');
        doc.text(`CID: ${ev.ipfs_cid}`, margin + 3, yPos + 9);
        yPos += 15;
        doc.setTextColor(0, 0, 0);

        doc.setFontSize(6);
        doc.text(`Verification URL: ${ev.ipfs_gateway_url || `https://gateway.pinata.cloud/ipfs/${ev.ipfs_cid}`}`, margin, yPos);
        yPos += 5;
      }

      // Chain of custody
      if (ev.chain_of_custody && ev.chain_of_custody.length > 0) {
        checkNewPage();
        doc.setFontSize(8);
        doc.setFont('helvetica', 'bold');
        doc.text('Chain of Custody:', margin, yPos + 3);
        yPos += 6;

        const custodyData = ev.chain_of_custody.slice(0, 5).map(c => [
          c.timestamp ? format(new Date(c.timestamp), 'MM/dd/yy HH:mm') : '',
          c.action || '',
          c.actor_type || '',
          c.signature ? c.signature.substring(0, 16) + '...' : ''
        ]);

        autoTable(doc, {
          startY: yPos,
          head: [['Timestamp', 'Action', 'Actor', 'Signature']],
          body: custodyData,
          theme: 'striped',
          styles: { fontSize: 6, cellPadding: 1 },
          headStyles: { fillColor: [100, 116, 139], fontSize: 6 },
          margin: { left: margin }
        });
        yPos = doc.lastAutoTable.finalY + 8;
      }
    }
  }

  checkNewPage();

  // ===== VERIFICATION INSTRUCTIONS =====
  doc.setFillColor(248, 250, 252);
  doc.rect(margin, yPos, pageWidth - 2 * margin, 8, 'F');
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text('VERIFICATION INSTRUCTIONS', margin + 3, yPos + 6);
  yPos += 12;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  yPos = addText(`IPFS: ${verification_instructions.ipfs}`, margin, yPos, pageWidth - 2 * margin, 7);
  yPos += 3;
  yPos = addText(`Blockchain: ${verification_instructions.blockchain}`, margin, yPos, pageWidth - 2 * margin, 7);
  yPos += 3;
  yPos = addText(`Chain of Custody: ${verification_instructions.chain_of_custody}`, margin, yPos, pageWidth - 2 * margin, 7);
  yPos += 8;

  // ===== LEGAL NOTICE =====
  checkNewPage();
  doc.setFillColor(254, 243, 199);
  doc.rect(margin, yPos, pageWidth - 2 * margin, 14, 'F');
  doc.setTextColor(146, 64, 14);
  doc.setFontSize(6);
  doc.setFont('helvetica', 'bold');
  doc.text('LEGAL NOTICE', margin + 3, yPos + 4);
  doc.setFont('helvetica', 'normal');
  const legalLines = doc.splitTextToSize(legal_notice, pageWidth - 2 * margin - 6);
  doc.text(legalLines, margin + 3, yPos + 8);

  // ===== FOOTER ON ALL PAGES =====
  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(7);
    doc.setTextColor(128, 128, 128);
    doc.text(
      `Page ${i} of ${pageCount} | JUSTICE Evidence Report | ${report_id}`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 8,
      { align: 'center' }
    );
  }

  return doc;
}

export function downloadEvidenceReport(doc, caseId) {
  doc.save(`JUSTICE_Evidence_Report_${caseId}.pdf`);
}
