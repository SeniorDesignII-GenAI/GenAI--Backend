/**
 * mlData contract — produced by backend/app.py (_build_ml_data).
 *
 * targetColumn:      string                         — chosen target
 * problemType:       "Classification" | "Regression"
 * datasetMeta:       { rows, cols, positiveRate }   — used in headers
 * leaderboard:       [{ rank, model, metric, score, trainTimeSec, isWinner }]
 * fullLeaderboard:   same shape, all candidates
 * runtime:           [{ stage, seconds }]
 * featureImportance: [{ feature, importance, direction: "positive"|"negative" }]
 * chartData:         {
 *   feature_1..feature_6: { feature, bands: [{ label, rate, count }] },
 *   is_classification: bool,
 *   positive_label:    string | null,
 * }
 *
 * This mock keeps the attrition example used during development — it's
 * only surfaced as a fallback when the live Node narrative server is
 * unavailable.
 */
export const mockMLData = {
  targetColumn: "Attrition",
  problemType: "Classification",
  datasetMeta: { rows: 8000, cols: 19, positiveRate: 0.163 },

  leaderboard: [
    { rank: 1, model: "Gradient Boosting Classifier", metric: "F1 (weighted)", score: 0.874, trainTimeSec: 12.4, isWinner: true },
    { rank: 2, model: "Random Forest Classifier",     metric: "F1 (weighted)", score: 0.851, trainTimeSec: 8.2,  isWinner: false },
    { rank: 3, model: "Extra Trees Classifier",       metric: "F1 (weighted)", score: 0.838, trainTimeSec: 6.7,  isWinner: false },
  ],
  fullLeaderboard: [
    { rank: 1, model: "Gradient Boosting Classifier", metric: "F1 (weighted)", score: 0.874, trainTimeSec: 12.4, isWinner: true },
    { rank: 2, model: "Random Forest Classifier",     metric: "F1 (weighted)", score: 0.851, trainTimeSec: 8.2,  isWinner: false },
    { rank: 3, model: "Extra Trees Classifier",       metric: "F1 (weighted)", score: 0.838, trainTimeSec: 6.7,  isWinner: false },
  ],

  runtime: [
    { stage: "Data Ingestion",      seconds: 0.4 },
    { stage: "Preprocessing",       seconds: 1.1 },
    { stage: "EDA",                 seconds: 0.8 },
    { stage: "Task Identification", seconds: 0.2 },
    { stage: "AutoML Tournament",   seconds: 27.3 },
    { stage: "ML Insights",         seconds: 4.6 },
  ],

  featureImportance: [
    { feature: "OvertimeHours",       importance: 0.184, direction: "positive" },
    { feature: "DistanceFromOffice",  importance: 0.142, direction: "positive" },
    { feature: "YearsSinceLastPromo", importance: 0.131, direction: "positive" },
    { feature: "JobSatisfaction",     importance: 0.118, direction: "negative" },
    { feature: "WorkLifeBalance",     importance: 0.097, direction: "negative" },
    { feature: "CompanyTenure",       importance: 0.082, direction: "negative" },
    { feature: "PerformanceScore",    importance: 0.071, direction: "negative" },
    { feature: "NumPromotions",       importance: 0.063, direction: "negative" },
  ],

  chartData: {
    is_classification: true,
    positive_label: "Yes",
    feature_1: {
      feature: "OvertimeHours",
      bands: [
        { label: "0",     rate: 0.08, count: 1500 },
        { label: "1–5",   rate: 0.13, count: 2200 },
        { label: "6–10",  rate: 0.21, count: 1800 },
        { label: "11–20", rate: 0.34, count: 1600 },
        { label: "20+",   rate: 0.46, count: 900  },
      ],
    },
    feature_2: {
      feature: "DistanceFromOffice",
      bands: [
        { label: "0–5",   rate: 0.09, count: 1820 },
        { label: "5–10",  rate: 0.12, count: 1640 },
        { label: "10–20", rate: 0.18, count: 2010 },
        { label: "20–30", rate: 0.24, count: 1290 },
        { label: "30–50", rate: 0.31, count: 870  },
        { label: "50+",   rate: 0.39, count: 370  },
      ],
    },
    feature_3: {
      feature: "YearsSinceLastPromo",
      bands: [
        { label: "0",  rate: 0.08, count: 1200 },
        { label: "1",  rate: 0.11, count: 1500 },
        { label: "2",  rate: 0.14, count: 1600 },
        { label: "3",  rate: 0.19, count: 1300 },
        { label: "4",  rate: 0.26, count: 1000 },
        { label: "5+", rate: 0.34, count: 1400 },
      ],
    },
    feature_4: {
      feature: "JobSatisfaction",
      bands: [
        { label: "Very Low",  rate: 0.41, count: 500  },
        { label: "Low",       rate: 0.28, count: 1200 },
        { label: "Medium",    rate: 0.17, count: 2800 },
        { label: "High",      rate: 0.09, count: 2600 },
        { label: "Very High", rate: 0.05, count: 900  },
      ],
    },
    feature_5: {
      feature: "WorkLifeBalance",
      bands: [
        { label: "Poor",      rate: 0.38, count: 600  },
        { label: "Fair",      rate: 0.22, count: 1900 },
        { label: "Good",      rate: 0.14, count: 3800 },
        { label: "Excellent", rate: 0.07, count: 1700 },
      ],
    },
    feature_6: {
      feature: "CompanyTenure",
      bands: [
        { label: "<1y",   rate: 0.32, count: 900  },
        { label: "1–3y",  rate: 0.22, count: 2400 },
        { label: "3–5y",  rate: 0.15, count: 1800 },
        { label: "5–10y", rate: 0.10, count: 2100 },
        { label: "10y+",  rate: 0.07, count: 800  },
      ],
    },
  },
};

/**
 * Mock narrative — markdown with <chart id="N" /> markers.
 * Shown only if the Claude narrative endpoint is unreachable.
 */
export const mockNarrative = `## Executive Summary

The model identifies attrition with an F1-weighted score of **0.874**, driven primarily by overtime, commute distance, and time since last promotion.

## Key Findings

Overtime hours are the single strongest predictor in the dataset.

<chart id="1" />

Commute distance shows a clean monotonic relationship with attrition.

<chart id="2" />

The feature importance ranking confirms which signals carry the most weight, separated by direction (red = risk-elevating, green = protective).

<chart id="5" />

A grid view of four secondary drivers shows how each independently moves attrition probability.

<chart id="6" />

## Developer Section

Model selection ran a 5-fold cross-validated tournament. Runtime breakdown and the full leaderboard are below.
`;
