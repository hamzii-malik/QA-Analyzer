export function normalizeAnalysisResult(rawResult) {
  if (!rawResult) {
    return {};
  }

  if (typeof rawResult === "string") {
    try {
      const parsed = JSON.parse(rawResult);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }

  if (typeof rawResult === "object") {
    return rawResult;
  }

  return {};
}
