import React, { useState, useEffect } from 'react';
import { 
  Upload, 
  ShieldCheck, 
  AlertCircle, 
  RefreshCw, 
  FileText, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  FolderOpen, 
  Sparkles, 
  CheckSquare, 
  Sliders
} from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000';

function App() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [selectedRow, setSelectedRow] = useState(null);
  const [activeInspectorTab, setActiveInspectorTab] = useState('audit'); // 'audit' | 'data' | 'documents'
  const [activeDocumentType, setActiveDocumentType] = useState(null); // 'SH_7' | 'BOARD_RESOLUTION' | etc.
  const [errorMsg, setErrorMsg] = useState('');
  const [dragOver, setDragOver] = useState(false);

  // Load table data on mount or after actions
  const fetchTable = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/table`);
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
        if (data.results && data.results.length > 0) {
          setSelectedRow(data.results[0]);
          // Pick first document type available
          const firstDocs = Object.keys(data.results[0].raw_documents || {});
          if (firstDocs.length > 0) {
            setActiveDocumentType(firstDocs[0]);
          }
        }
      }
    } catch (e) {
      console.error("Failed to fetch capital table", e);
    }
  };

  useEffect(() => {
    fetchTable();
  }, []);

  const handlePreloadLocal = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await fetch(`${API_BASE}/api/preload-local`, { method: 'POST' });
      if (!res.ok) {
        throw new Error("Failed to preload local workspace dataset.");
      }
      const data = await res.json();
      setResults(data.results || []);
      if (data.results && data.results.length > 0) {
        setSelectedRow(data.results[0]);
        const firstDocs = Object.keys(data.results[0].raw_documents || {});
        if (firstDocs.length > 0) {
          setActiveDocumentType(firstDocs[0]);
        }
      }
    } catch (e) {
      setErrorMsg("Backend server is not running. Please start the FastAPI backend on port 8000 first.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      await fetch(`${API_BASE}/api/reset`, { method: 'POST' });
      setResults([]);
      setSelectedRow(null);
      setActiveDocumentType(null);
    } catch (e) {
      setErrorMsg("Failed to reset backend cache.");
    } finally {
      setLoading(false);
    }
  };

  // Drag and drop ingestion
  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      await uploadFiles(files);
    }
  };

  const handleFileSelect = async (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      await uploadFiles(files);
    }
  };

  const uploadFiles = async (files) => {
    setLoading(true);
    setErrorMsg('');
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    try {
      const res = await fetch(`${API_BASE}/api/ingest`, {
        method: 'POST',
        body: formData
      });
      if (!res.ok) {
        throw new Error("Ingest request failed.");
      }
      const data = await res.json();
      setResults(data.results || []);
      if (data.results && data.results.length > 0) {
        setSelectedRow(data.results[0]);
        const firstDocs = Object.keys(data.results[0].raw_documents || {});
        if (firstDocs.length > 0) {
          setActiveDocumentType(firstDocs[0]);
        }
      }
    } catch (e) {
      setErrorMsg("Failed to upload and ingest filings. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const handleRowClick = (row) => {
    setSelectedRow(row);
    const docTypes = Object.keys(row.raw_documents || {});
    if (docTypes.length > 0 && (!activeDocumentType || !row.raw_documents[activeDocumentType])) {
      setActiveDocumentType(docTypes[0]);
    }
  };

  // Formatting helpers
  const formatCurrency = (val) => {
    if (val === undefined || val === null) return '-';
    if (typeof val === 'string') return val;
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };

  const getParticulars = (row) => {
    const before = formatCurrency(row.total_capital_before);
    const after = formatCurrency(row.total_capital_after);
    const diff = row.total_capital_after - row.total_capital_before;
    
    if (row.event_id === 'Event1') {
      return `Authorised capital increased from ${before} to ${after} by creating 4,90,000 Equity Shares.`;
    } else if (row.event_id === 'Event2') {
      return `Authorised capital increased from ${before} to ${after} by creating 10,00,000 Equity Shares and 5,00,000 Series A CCPS.`;
    } else if (row.event_id === 'Event3') {
      return `Authorised capital increased from ${before} to ${after} by creating 20,00,000 Equity Shares and 10,00,000 Series B CCPS.`;
    }
    return `Increase in Authorised Capital of ${formatCurrency(diff)}.`;
  };

  return (
    <div className="app-container animate-fade-in">
      {/* Header */}
      <header className="dashboard-header">
        <div>
          <div className="company-badge">
            <Sparkles size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            ZetaTech Solutions Private Limited
          </div>
          <h1 className="main-title">DRHP Capital Structure Agent</h1>
          <p className="sub-title">Automated classification, extraction, and multi-doc verification engine for filings</p>
        </div>
        <div className="action-buttons">
          <button className="btn btn-secondary" onClick={handleReset} disabled={loading}>
            <RefreshCw size={16} />
            Reset Cache
          </button>
          <button className="btn btn-primary" onClick={handlePreloadLocal} disabled={loading}>
            <FolderOpen size={16} />
            Load Workspace Dataset
          </button>
        </div>
      </header>

      {/* Error Alerts */}
      {errorMsg && (
        <div className="glass-panel" style={{ borderColor: 'var(--color-danger)', background: 'var(--color-danger-bg)', padding: '1rem 1.5rem', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <AlertCircle color="var(--color-danger)" size={20} />
          <span style={{ color: 'var(--text-primary)', fontSize: '0.9rem', fontWeight: 500 }}>{errorMsg}</span>
        </div>
      )}

      {/* Upload Zone */}
      {results.length === 0 && (
        <div 
          className={`upload-zone glass-panel ${dragOver ? 'dragover' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input 
            type="file" 
            id="file-upload" 
            multiple 
            onChange={handleFileSelect} 
            style={{ display: 'none' }} 
          />
          <label htmlFor="file-upload" style={{ cursor: 'pointer' }}>
            <Upload className="upload-icon" />
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.25rem' }}>Drag & Drop filings folder here</h3>
            <p style={{ margin: '0 0 1.5rem 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Upload Form SH-7, Board Resolutions, EGM Notices, and MOA attachments (TXT files).
            </p>
            <span className="btn btn-primary">
              <FileText size={16} />
              Select Files Manually
            </span>
          </label>
        </div>
      )}

      {results.length > 0 && (
        <div className="dashboard-grid animate-fade-in">
          {/* Left Column: Compiled DRHP Table */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            
            <div className="glass-panel table-card">
              <div className="table-header">
                <h3 className="table-title">
                  <ShieldCheck size={20} color="var(--accent-primary)" />
                  Consolidated DRHP Authorised Share Capital Change Table
                </h3>
                <span className="badge badge-success" style={{ fontSize: '0.75rem' }}>
                  {results.filter(r => r.status === 'Confirmed').length}/{results.length} Verified
                </span>
              </div>
              <div className="table-wrapper">
                <table className="premium-table">
                  <thead>
                    <tr>
                      <th>Date of Meeting / Resolution</th>
                      <th>Particulars of Capital Alteration</th>
                      <th>Pre-Event Capital (INR)</th>
                      <th>Post-Event Capital (INR)</th>
                      <th>AGM / EGM</th>
                      <th>Verification Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((row) => (
                      <tr 
                        key={row.event_id} 
                        className={selectedRow?.event_id === row.event_id ? 'selected' : ''}
                        onClick={() => handleRowClick(row)}
                      >
                        <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                          {row.egm_date || "[UNVERIFIED — date missing]"}
                        </td>
                        <td style={{ fontSize: '0.88rem', maxWidth: '350px' }}>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                            {row.title}
                          </div>
                          <div style={{ color: 'var(--text-secondary)' }}>
                            {getParticulars(row)}
                          </div>
                        </td>
                        <td style={{ fontFamily: 'Fira Code', fontSize: '0.85rem' }}>
                          {formatCurrency(row.total_capital_before)}
                        </td>
                        <td style={{ fontFamily: 'Fira Code', fontSize: '0.85rem', fontWeight: 600 }}>
                          {formatCurrency(row.total_capital_after)}
                        </td>
                        <td style={{ fontFamily: 'Outfit', fontSize: '0.85rem', fontWeight: 700, textAlign: 'center' }}>
                          <span style={{ background: 'hsla(230, 25%, 20%, 0.5)', padding: '0.25rem 0.6rem', borderRadius: '6px', border: '1px solid var(--border-color)', color: 'var(--accent-secondary)' }}>
                            {row.meeting_type || "EGM"}
                          </span>
                        </td>
                        <td>
                          {row.status === 'Confirmed' ? (
                            <span className="badge badge-success">
                              <CheckCircle2 size={12} />
                              Confirmed
                            </span>
                          ) : (
                            <span className="badge badge-warning">
                              <AlertTriangle size={12} />
                              Flagged
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Verification Helper Details */}
            <div className="glass-panel" style={{ padding: '1.5rem 2rem' }}>
              <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', display: 'flex', alignItem: 'center', gap: '0.5rem' }}>
                <CheckSquare size={18} color="var(--accent-primary)" />
                Drafting Agent Compliance Checklists
              </h3>
              <p style={{ margin: '0 0 1.25rem 0', color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeght: 1.5 }}>
                Form SH-7 (pursuant to Section 64 of Companies Act 2013) demands that the company notify the ROC within 30 days of the resolution. The agent verifies filings in the background, matching totals and resolving dates.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                  <CheckCircle2 size={14} color="var(--color-success)" style={{ marginTop: '2px' }} />
                  <span>Cross-references shareholders EGM notices to ensure meeting dates correspond.</span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                  <CheckCircle2 size={14} color="var(--color-success)" style={{ marginTop: '2px' }} />
                  <span>Validates board resolutions and traces whether they precede EGM calls.</span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                  <CheckCircle2 size={14} color="var(--color-success)" style={{ marginTop: '2px' }} />
                  <span>Scrutinizes amended MOA Capital Clause V to double check class balances.</span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', color: 'var(--text-secondary)' }}>
                  <CheckCircle2 size={14} color="var(--color-success)" style={{ marginTop: '2px' }} />
                  <span>Flags any draft, unsigned, or mismatched regulatory filings automatically.</span>
                </div>
              </div>
            </div>

          </div>

          {/* Right Column: Metadata Inspector */}
          {selectedRow && (
            <div className="glass-panel inspector-card animate-fade-in">
              <div className="inspector-header">
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.15rem' }}>Filing Metadata Inspector</h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{selectedRow.title}</span>
                </div>
                {selectedRow.status === 'Confirmed' ? (
                  <span className="badge badge-success">
                    <CheckCircle2 size={12} />
                    Verified
                  </span>
                ) : (
                  <span className="badge badge-warning">
                    <AlertTriangle size={12} />
                    {selectedRow.anomalies.length} Alerts
                  </span>
                )}
              </div>

              <div className="inspector-tabs">
                <button 
                  className={`tab-btn ${activeInspectorTab === 'audit' ? 'active' : ''}`}
                  onClick={() => setActiveInspectorTab('audit')}
                >
                  <CheckSquare size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                  Audit Logs
                </button>
                <button 
                  className={`tab-btn ${activeInspectorTab === 'data' ? 'active' : ''}`}
                  onClick={() => setActiveInspectorTab('data')}
                >
                  <Sliders size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                  Extracted Specs
                </button>
                <button 
                  className={`tab-btn ${activeInspectorTab === 'documents' ? 'active' : ''}`}
                  onClick={() => setActiveInspectorTab('documents')}
                >
                  <FileText size={14} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                  Source Files
                </button>
              </div>

              <div className="inspector-content">
                {/* Audit Logs Tab */}
                {activeInspectorTab === 'audit' && (
                  <div>
                    <h4 style={{ margin: '0 0 1rem 0', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>Verification Checks</h4>
                    {selectedRow.verification_logs.map((log, index) => (
                      <div className="log-item" key={index}>
                        <div className="log-icon">
                          {log.status === 'PASS' && <CheckCircle2 size={18} color="var(--color-success)" />}
                          {log.status === 'WARN' && <AlertTriangle size={18} color="var(--color-warning)" />}
                          {log.status === 'FAIL' && <XCircle size={18} color="var(--color-danger)" />}
                        </div>
                        <div className="log-details">
                          <h4>{log.label}</h4>
                          <p>{log.message}</p>
                        </div>
                      </div>
                    ))}

                    {selectedRow.anomalies.length > 0 && (
                      <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'var(--color-danger-bg)', borderRadius: '8px', border: '1px solid hsla(355, 85%, 55%, 0.2)' }}>
                        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: 'var(--color-danger)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <AlertCircle size={16} />
                          Anomalies & Gaps Detected
                        </h4>
                        <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-primary)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          {selectedRow.anomalies.map((anom, idx) => (
                            <li key={idx}>{anom}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Extracted Specs Tab */}
                {activeInspectorTab === 'data' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <h4 style={{ margin: '0', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>Extracted Parameter Registry</h4>
                    
                    <div className="parameter-grid">
                      <div className="parameter-card">
                        <label>EGM / Resolution Date</label>
                        <span>{selectedRow.egm_date || '-'}</span>
                      </div>
                      <div className="parameter-card">
                        <label>Filing Date</label>
                        <span>{selectedRow.sh7_filing_date || '-'}</span>
                      </div>
                      <div className="parameter-card">
                        <label>Total Pre Capital</label>
                        <span style={{ fontFamily: 'Fira Code', fontSize: '0.9rem' }}>{formatCurrency(selectedRow.total_capital_before)}</span>
                      </div>
                      <div className="parameter-card">
                        <label>Total Post Capital</label>
                        <span style={{ fontFamily: 'Fira Code', fontSize: '0.9rem' }}>{formatCurrency(selectedRow.total_capital_after)}</span>
                      </div>
                      <div className="parameter-card">
                        <label>Equity Shares Post</label>
                        <span>{selectedRow.equity_shares_after ? selectedRow.equity_shares_after.toLocaleString('en-IN') : '0'} Shares</span>
                      </div>
                      <div className="parameter-card">
                        <label>Preference Shares Post</label>
                        <span>{selectedRow.pref_shares_after ? selectedRow.pref_shares_after.toLocaleString('en-IN') : '0'} Shares</span>
                      </div>
                    </div>

                    <div className="parameter-card" style={{ width: '100%', boxSizing: 'border-box' }}>
                      <label>Preference Share Details / Class</label>
                      <span style={{ fontSize: '0.9rem' }}>{selectedRow.pref_class_after || 'NIL'}</span>
                    </div>

                    <div className="parameter-card" style={{ width: '100%', boxSizing: 'border-box' }}>
                      <label>Active Filers & Signatories</label>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.25rem' }}>
                        {Object.entries(selectedRow.raw_documents).map(([type, doc]) => (
                          <div key={type} style={{ display: 'flex', justifyContent: 'between', fontSize: '0.85rem', borderBottom: '1px solid hsla(230,25%,25%,0.15)', paddingBottom: '0.25rem' }}>
                            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>{type}:</span>
                            <span style={{ marginLeft: 'auto', color: 'var(--text-primary)' }}>
                              {doc.parsed_data.signatory_name || doc.parsed_data.signatory_din || 'N/A'} 
                              {doc.classification.filing_status === 'DRAFT' && ' [DRAFT]'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Source Files Tab */}
                {activeInspectorTab === 'documents' && (
                  <div className="raw-viewer animate-fade-in">
                    <div className="raw-doc-selector">
                      {Object.keys(selectedRow.raw_documents).map((docType) => (
                        <button
                          key={docType}
                          className={`raw-tab ${activeDocumentType === docType ? 'active' : ''}`}
                          onClick={() => setActiveDocumentType(docType)}
                        >
                          {docType.replace('_', ' ')}
                        </button>
                      ))}
                    </div>

                    {activeDocumentType && selectedRow.raw_documents[activeDocumentType] && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            File: <strong style={{ color: 'var(--text-secondary)' }}>{selectedRow.raw_documents[activeDocumentType].filename}</strong>
                          </span>
                          <span className={`badge ${selectedRow.raw_documents[activeDocumentType].classification.filing_status === 'DRAFT' ? 'badge-warning' : 'badge-success'}`} style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem', marginLeft: 'auto' }}>
                            {selectedRow.raw_documents[activeDocumentType].classification.filing_status}
                          </span>
                        </div>
                        <div className="raw-code-box">
                          {selectedRow.raw_documents[activeDocumentType].content}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
