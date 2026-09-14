import { Component, useEffect, useState } from "react";
import {
  getAnalyses,
  getAnalysis,
  uploadAndAnalyze,
  getProjectAnalysisStatus,
  startProjectAnalysis,
} from "./api";
import { normalizeAnalysisResult } from "./analysisUtils";
import "./App.css";


class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="results-section">
          <div className="error-message">
            ⚠ Something went wrong while rendering the analysis result. Please try again or refresh the page.
          </div>
        </section>
      );
    }

    return this.props.children;
  }
}


function App() {
  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [projectAnalysis, setProjectAnalysis] = useState(null);
  const [history, setHistory] = useState([]);
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);

  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadHistory();
  }, []);


  async function loadHistory() {
    try {
      setHistoryLoading(true);

      const data = await getAnalyses();

      setHistory(data.analyses || []);
      setError("");
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to load analysis history.");
    } finally {
      setHistoryLoading(false);
    }
  }


  async function handleAnalyze() {
    if (!file) {
      setError("Please select a source-code file or project ZIP first.");
      return;
    }

    setError("");
    setAnalysis(null);
    setProjectAnalysis(null);
    setSelectedAnalysis(null);
    setLoading(true);

    try {
      const extension = (file.name || "").split(".").pop()?.toLowerCase();
      const isArchive = ["zip", "rar"].includes(extension);

      if (isArchive) {
        const job = await startProjectAnalysis(file);
        setProgress(job);

        let status = job;
        while (status.status !== "completed" && status.status !== "failed") {
          await new Promise((resolve) => setTimeout(resolve, 700));
          status = await getProjectAnalysisStatus(job.job_id);
          setProgress(status);
        }

        if (status.status === "failed") {
          throw new Error(status.error || "Project archive analysis failed.");
        }

        setProjectAnalysis(status.result);
      } else {
        setProgress({ phase: "testing", current_file: file.name, extraction_percent: 100, progress_percent: 50, analysis_step: "Analyzing uploaded source file" });
        const data = await uploadAndAnalyze(file);
        setAnalysis(data.analysis);
      }

      await loadHistory();
    } catch (err) {
      setError(err.message || "Analysis failed.");
    } finally {
      setLoading(false);
      setProgress(null);
    }
  }


  async function handleViewAnalysis(id) {
    try {
      setError("");

      const data = await getAnalysis(id);
      const record = data.analysis;

      if (record?.analysis_type === "project_qa") {
        setProjectAnalysis(normalizeAnalysisResult(record.result));
        setAnalysis(null);
        setSelectedAnalysis(null);
        window.scrollTo({
          top: 0,
          behavior: "smooth",
        });
        return;
      }

      const normalized = {
        ...record,
        result: normalizeAnalysisResult(record?.result),
      };

      setSelectedAnalysis(normalized);
      setAnalysis(null);
      setProjectAnalysis(null);

      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    } catch (err) {
      setError(err.message || "Unable to load analysis.");
    }
  }


  function handleFileChange(event) {
    const selectedFile = event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    setFile(selectedFile);
    setError("");
    setAnalysis(null);
    setSelectedAnalysis(null);
  }


  function getScoreClass(score) {
    if (score >= 80) {
      return "score-good";
    }

    if (score >= 50) {
      return "score-medium";
    }

    return "score-bad";
  }


  function renderList(items) {
    if (!items || items.length === 0) {
      return (
        <div className="empty-list">
          No issues found.
        </div>
      );
    }

    return (
      <ul className="result-list">
        {items.map((item, index) => (
          <li key={index}>
            {typeof item === "string"
              ? item
              : JSON.stringify(item)}
          </li>
        ))}
      </ul>
    );
  }

  function renderEvidenceList(items, emptyMessage = "No evidence found.") {
    if (!items || items.length === 0) {
      return <div className="empty-list">{emptyMessage}</div>;
    }

    return (
      <ul className="result-list">
        {items.map((item, index) => (
          <li key={`${item.category || item.tool || "evidence"}-${index}`}>
            {typeof item === "string" ? item : (
              <>
                {item.file && <strong>{item.file}{item.line ? `:${item.line}` : ""}: </strong>}
                {item.condition && <strong>{item.condition} </strong>}
                {item.input_family && <strong>{item.input_family}: </strong>}
                {item.name && <strong>{item.name}: </strong>}
                {item.message || item.description || item.reason || (item.test_cases ? `Test cases: ${JSON.stringify(item.test_cases)}` : JSON.stringify(item))}
              </>
            )}
          </li>
        ))}
      </ul>
    );
  }


  function renderProjectAnalysis(data) {
    if (!data) {
      return null;
    }

    const categories = data.categories || {};
    const categoryEntries = Object.entries(categories);
    const score = Number(data.overall_score || 0);
    const detection = data.project_detection || {};
    const securitySummary = data.security?.summary || {};
    const testing = data.testing || {};
    const testingTotal = Object.values(testing).reduce(
      (total, item) => total + Number(item?.summary?.total || 0),
      0
    );

    return (
      <section className="results-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">PROJECT QA RESULT</p>
            <h2>{data.project_name || "Project Quality Report"}</h2>
          </div>
          <span className="status-badge">Completed</span>
        </div>

        <div className="score-card">
          <div className="score-circle">
            <span className={getScoreClass(score)}>{score}</span>
          </div>

          <div className="score-content">
            <h3>Overall Project Quality Score</h3>
            <p>{data.summary || "Project QA summary is not available yet."}</p>
          </div>
        </div>

        <div className="stats-grid">
          <div className="stat-card">
            <span>Languages</span>
            <strong>{detection.languages?.join(", ") || "Not detected"}</strong>
          </div>
          <div className="stat-card">
            <span>Frameworks</span>
            <strong>{detection.frameworks?.join(", ") || "Not detected"}</strong>
          </div>
          <div className="stat-card">
            <span>Security Findings</span>
            <strong>{securitySummary.total || 0}</strong>
          </div>
          <div className="stat-card">
            <span>Generated Test Cases</span>
            <strong>{testingTotal}</strong>
          </div>

          <div className="stat-card">
            <span>Reports</span>
            <strong>
              {data.report_url ? (
                <>
                  <a className="report-link" href={data.report_url} target="_blank" rel="noreferrer">DOCX</a>{" "}
                  {data.html_report_url && <a className="report-link" href={data.html_report_url} target="_blank" rel="noreferrer">HTML</a>}{" "}
                  {data.json_report_url && <a className="report-link" href={data.json_report_url} target="_blank" rel="noreferrer">JSON</a>}
                </>
              ) : "Pending"}
            </strong>
          </div>
        </div>

        {data.score_breakdown && (
          <div className="project-overview-card">
            <div className="card-title">
              <span className="icon testing">✓</span>
              <h3>Transparent Score</h3>
            </div>
            <p>
              Base {data.score_breakdown.base} - security deductions {data.score_breakdown.security_deductions} = final {data.score_breakdown.final}
            </p>
          </div>
        )}

        {data.security && (
          <div className="project-overview-card">
            <div className="card-title">
              <span className="icon security">!</span>
              <h3>Security Scanners</h3>
            </div>
            <ul className="result-list">
              {Object.entries(data.security.scanners || {}).map(([scanner, scannerData]) => (
                <li key={scanner}>
                  {scanner}: {scannerData.status} ({scannerData.summary?.total || 0} findings)
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="results-grid">
          <div className="result-card security-result-card">
            <div className="card-title">
              <span className="icon security">🔐</span>
              <h3>Security Testing Results</h3>
            </div>
            {Object.entries(data.security?.scanners || {}).map(([scanner, scannerData]) => (
              <div className="evidence-group" key={scanner}>
                <div className="category-meta">
                  <strong>{scanner.toUpperCase()}</strong> | Status: {scannerData.status} | Findings: {scannerData.summary?.total || 0}
                </div>
                {renderEvidenceList(scannerData.findings, `${scanner} found no security issues.`)}
                {scannerData.errors?.length > 0 && (
                  <div className="category-command">{scannerData.errors.join(" ")}</div>
                )}
              </div>
            ))}
            {!Object.keys(data.security?.scanners || {}).length && (
              <div className="empty-list">Security scanners did not return results.</div>
            )}
          </div>

          <div className="result-card testing-result-card">
            <div className="card-title">
              <span className="icon testing">🧪</span>
              <h3>Edge Case Testing Results</h3>
            </div>
            <div className="category-meta">
              Status: {data.testing?.edge?.status || "pending"} | Cases: {data.testing?.edge?.summary?.total || 0}
            </div>
            {renderEvidenceList(data.testing?.edge?.findings, "No edge-case families generated.")}
            {data.testing?.edge?.findings?.map((family) => (
              <div className="category-command" key={family.input_family}>
                <strong>{family.input_family}:</strong> {JSON.stringify(family.test_cases)}
              </div>
            ))}
          </div>
        </div>

        <div className="results-grid">
          {Object.entries(data.testing || {})
            .filter(([name]) => name !== "edge")
            .map(([name, testingData]) => (
              <div className="result-card" key={`testing-${name}`}>
                <div className="card-title">
                  <span className="icon testing">✓</span>
                  <h3>{name.replace(/_/g, " ")} Testing</h3>
                </div>
                <div className="category-meta">
                  Status: {testingData.status || "pending"} | Cases: {testingData.summary?.total || 0}
                </div>
                {renderEvidenceList(testingData.findings, "No findings generated.")}
              </div>
            ))}
        </div>

        <div className="project-overview-card">
          <div className="card-title">
            <span className="icon testing">📊</span>
            <h3>Execution Overview</h3>
          </div>
          <ul className="result-list">
            {categoryEntries
              .filter(([, categoryData]) => categoryData?.status === "ready")
              .slice(0, 4)
              .map(([categoryName, categoryData]) => (
                <li key={`${categoryName}-overview`}>
                  {categoryName.replace(/_/g, " ").toUpperCase()}: {categoryData.score || 0}/100
                </li>
              ))}
          </ul>
        </div>

        {data.external_checks && (
          <div className="project-overview-card">
            <div className="card-title">
              <span className="icon testing">🧰</span>
              <h3>External QA Tools</h3>
            </div>
            <ul className="result-list">
              {Object.entries(data.external_checks).map(([toolName, toolData]) => (
                <li key={toolName}>
                  {toolName.toUpperCase()}: {toolData.status}
                  {toolData.details?.[0] ? ` — ${toolData.details[0]}` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="stats-grid">
          <div className="stat-card">
            <span>Project Type</span>
            <strong>{data.project_type || "generic"}</strong>
          </div>

          <div className="stat-card">
            <span>Files Scanned</span>
            <strong>{data.files_scanned || 0}</strong>
          </div>

          <div className="stat-card">
            <span>Categories</span>
            <strong>{categoryEntries.length}</strong>
          </div>

          <div className="stat-card">
            <span>Report</span>
            <strong>
              {data.report_url ? (
                <a className="report-link" href={data.report_url} target="_blank" rel="noreferrer">
                  Open DOCX
                </a>
              ) : (
                "Pending"
              )}
            </strong>
          </div>
        </div>

        <div className="results-grid">
          {categoryEntries.map(([categoryName, categoryData]) => (
            <div className="result-card" key={categoryName}>
              <div className="card-title">
                <span className="icon testing">🧪</span>
                <h3>{categoryName.replace(/_/g, " ")}</h3>
              </div>

              <div className="empty-list">
                Status: {categoryData.status || "pending"} | Score: {categoryData.score || 0}
              </div>

              {categoryData.tool && (
                <div className="category-meta">
                  <strong>Tool:</strong> {categoryData.tool}
                </div>
              )}

              {categoryData.command && (
                <div className="category-command">
                  <strong>Command:</strong> {categoryData.command}
                </div>
              )}

              <ul className="result-list">
                {(categoryData.details || []).map((detail, index) => (
                  <li key={`${categoryName}-${index}`}>{detail}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>
    );
  }

  function renderAnalysis(data) {
    if (!data) {
      return null;
    }

    const ai = data.ai_analysis;
    const rule = data.rule_based_analysis;

    const score = ai?.overall_score ?? 0;

    return (
      <section className="results-section">

        <div className="section-heading">
          <div>
            <p className="eyebrow">ANALYSIS RESULT</p>
            <h2>Quality Report</h2>
          </div>

          <span className="status-badge">
            Completed
          </span>
        </div>


        <div className="score-card">

          <div className="score-circle">
            <span className={getScoreClass(score)}>
              {score}
            </span>
          </div>

          <div className="score-content">
            <h3>Overall Quality Score</h3>

            <p>
              {ai?.summary ||
                "No AI summary was provided."}
            </p>
          </div>

        </div>


        <div className="stats-grid">

          <div className="stat-card">
            <span>Lines</span>
            <strong>
              {rule?.summary?.total_lines ?? 0}
            </strong>
          </div>

          <div className="stat-card">
            <span>Characters</span>
            <strong>
              {rule?.summary?.total_characters ?? 0}
            </strong>
          </div>

          <div className="stat-card">
            <span>Rule Issues</span>
            <strong>
              {rule?.summary?.issues_found ?? 0}
            </strong>
          </div>

          <div className="stat-card">
            <span>AI Bugs</span>
            <strong>
              {ai?.bugs?.length ?? 0}
            </strong>
          </div>

        </div>


        <div className="results-grid">

          <div className="result-card">
            <div className="card-title">
              <span className="icon danger">🐛</span>
              <h3>Bugs</h3>
            </div>

            {renderList(ai?.bugs)}
          </div>


          <div className="result-card">
            <div className="card-title">
              <span className="icon security">🔐</span>
              <h3>Security Issues</h3>
            </div>

            {renderList(ai?.security_issues)}
          </div>


          <div className="result-card">
            <div className="card-title">
              <span className="icon quality">🧹</span>
              <h3>Code Quality</h3>
            </div>

            {renderList(ai?.code_quality_issues)}
          </div>


          <div className="result-card">
            <div className="card-title">
              <span className="icon testing">🧪</span>
              <h3>Test Cases</h3>
            </div>

            {renderList(ai?.test_cases)}
          </div>

        </div>


        <div className="recommendations-card">

          <div className="card-title">
            <span className="icon recommendation">
              💡
            </span>

            <h3>Recommendations</h3>
          </div>

          {renderList(ai?.recommendations)}

        </div>


        {rule?.suggestions?.length > 0 && (
          <div className="recommendations-card">

            <div className="card-title">
              <span className="icon suggestion">
                ⚡
              </span>

              <h3>Automated Suggestions</h3>
            </div>

            {renderList(rule.suggestions)}

          </div>
        )}

      </section>
    );
  }


  return (
    <div className="app">

      <header className="topbar">

        <div className="brand">

          <div className="brand-icon">
            QA
          </div>

          <div>
            <h1>QA Analyzer</h1>
            <span>
              AI-Powered Software Quality Analysis
            </span>
          </div>

        </div>


        <div className="backend-status">
          <span className="status-dot"></span>
          Backend Connected
        </div>

      </header>


      <main className="container">

        <section className="hero">

          <div className="hero-text">

            <p className="eyebrow">
              INTELLIGENT CODE REVIEW
            </p>

            <h2>
              Analyze your code with
              <span> AI-powered QA</span>
            </h2>

            <p>
              Upload your source code and get automated
              bug detection, security analysis, code quality
              insights and test-case recommendations.
            </p>

          </div>

        </section>


        <section className="upload-card">

          <div className="upload-header">

            <div>
              <p className="eyebrow">
                START ANALYSIS
              </p>

              <h2>
                Upload Source Code
              </h2>
            </div>

            <div className="upload-icon">
              ↑
            </div>

          </div>


          <label className="drop-zone">

            <input
              type="file"
              onChange={handleFileChange}
              accept=".zip,.rar,.py,.js,.jsx,.ts,.tsx,.java,.cpp,.c,.cs,.php,.go,.rs,.html,.css,.sql"
            />

            <div className="upload-symbol">
              ☁
            </div>

            <h3>
              {file
                ? file.name
                : "Choose a project ZIP or source-code file"}
            </h3>

            <p>
              {file
                ? `${(file.size / 1024).toFixed(1)} KB selected`
                : "ZIP project archive or single file: Python, JavaScript, TypeScript, Java, C++, C#, PHP, Go, Rust, HTML, CSS or SQL"}
            </p>

          </label>


          {error && (
            <div className="error-message">
              ⚠ {error}
            </div>
          )}

          {loading && progress && (
            <div className="progress-panel" aria-live="polite">
              <div className="progress-heading">
                <strong>
                  {progress.phase === "extracting"
                    ? "Extracting project"
                    : progress.phase === "scanning"
                      ? "Scanning files"
                      : progress.phase === "reporting"
                        ? "Generating report"
                      : "Testing project"}
                </strong>
                <span>{progress.progress_percent || 0}% overall</span>
              </div>
              <div className="progress-track">
                <div className="progress-value" style={{ width: `${progress.progress_percent || 3}%` }} />
              </div>
              <div className="progress-file">
                <span>Analyzing:</span> {progress.analysis_step || "Preparing analysis"}
              </div>
              <div className="progress-file">
                <span>Extraction:</span> {progress.extraction_percent || 0}% complete
              </div>
              <div className="progress-file">
                <span>Current:</span> {progress.current_file || "Preparing..."}
              </div>
              <div className="progress-file">
                <span>Files scanned:</span> {progress.files_scanned || 0}
              </div>
            </div>
          )}


          <button
            className="analyze-button"
            onClick={handleAnalyze}
            disabled={loading || !file}
          >

            {loading ? (
              <>
                <span className="spinner"></span>
                QA engine is analyzing...
              </>
            ) : (
              <>
                Analyze File
                <span>→</span>
              </>
            )}

          </button>

        </section>


        {projectAnalysis && (
          <ErrorBoundary>
            {renderProjectAnalysis(projectAnalysis)}
          </ErrorBoundary>
        )}

        {(analysis || selectedAnalysis) && (
          <ErrorBoundary>
            {renderAnalysis(
              analysis || normalizeAnalysisResult(selectedAnalysis?.result)
            )}
          </ErrorBoundary>
        )}


        <section className="history-section">

          <div className="section-heading">

            <div>
              <p className="eyebrow">
                HISTORY
              </p>

              <h2>
                Recent Analyses
              </h2>
            </div>

            <button
              className="refresh-button"
              onClick={loadHistory}
            >
              ↻ Refresh
            </button>

          </div>


          <div className="history-card">

            {historyLoading ? (
              <div className="history-empty">
                Loading analysis history...
              </div>
            ) : history.length === 0 ? (
              <div className="history-empty">
                No analyses found yet.
              </div>
            ) : (
              <div className="history-table">

                <div className="history-row history-header">
                  <span>ID</span>
                  <span>File</span>
                  <span>Type</span>
                  <span>Status</span>
                  <span>Action</span>
                </div>


                {history.map((item) => (
                  <div
                    className="history-row"
                    key={item.id}
                  >

                    <span className="analysis-id">
                      #{item.id}
                    </span>

                    <span className="file-name">
                      {item.file_name}
                    </span>

                    <span>
                      {item.analysis_type}
                    </span>

                    <span>
                      <span className="table-status">
                        {item.status}
                      </span>
                    </span>

                    <span>
                      <button
                        className="view-button"
                        onClick={() =>
                          handleViewAnalysis(item.id)
                        }
                      >
                        View
                      </button>
                    </span>

                  </div>
                ))}

              </div>
            )}

          </div>

        </section>

      </main>


      <footer>
        <p>
          QA Analyzer • AI-powered software quality
          assurance
        </p>
      </footer>

    </div>
  );
}

export default App;