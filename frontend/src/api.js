const API_BASE_URL = import.meta.env.VITE_API_URL || "";

async function request(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  }
  return data;
}

export async function uploadAndAnalyze(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_BASE_URL}/api/upload/analyze`,
    {
      method: "POST",
      body: formData,
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail)
    );
  }

  return data;
}

export async function uploadProjectArchive(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(
    `${API_BASE_URL}/api/upload/project`,
    {
      method: "POST",
      body: formData,
    }
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail)
    );
  }

  return data;
}

export async function startProjectAnalysis(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/upload/project/start`, {
    method: "POST",
    body: formData,
  });
  const data = await response.json();

  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  }

  return data;
}

export async function getProjectAnalysisStatus(jobId) {
  const response = await fetch(`${API_BASE_URL}/api/upload/project/status/${jobId}`);
  const data = await response.json();

  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  }

  return data;
}

export async function getAnalyses() {
  const response = await fetch(
    `${API_BASE_URL}/api/analysis/`
  );

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail)
    );
  }

  return data;
}

export async function getAnalysis(id) {
  return request(`/api/analysis/${id}`);
}

export const getAnalysisStatus = (id) => request(`/api/analysis/${id}/status`);
export const getAnalysisResults = (id) => request(`/api/analysis/${id}/results`);
export const getSecurityResults = (id) => request(`/api/analysis/${id}/security`);
export const getTestResults = (id) => request(`/api/analysis/${id}/tests`);
export const getFindings = (id) => request(`/api/analysis/${id}/findings`);
export const getReport = (id) => request(`/api/analysis/${id}/report`);
export const cancelAnalysis = (id) => request(`/api/analysis/${id}/cancel`, { method: "POST" });