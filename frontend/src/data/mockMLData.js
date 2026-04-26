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

  chartData: [
    {
      id: 1,
      title: "Attrition Rate by Overtime Band",
      insight: "Attrition risk climbs as overtime increases.",
      chartType: "BarChart",
      xKey: "overtime_band",
      yKeys: ["attrition_rate"],
      data: [
        { overtime_band: "0", attrition_rate: 0.08 },
        { overtime_band: "1-5", attrition_rate: 0.13 },
        { overtime_band: "6-10", attrition_rate: 0.21 },
        { overtime_band: "11-20", attrition_rate: 0.34 },
        { overtime_band: "20+", attrition_rate: 0.46 },
      ],
    },
    {
      id: 2,
      title: "Attrition Rate by Commute Distance",
      insight: "Longer commute is associated with higher attrition.",
      chartType: "LineChart",
      xKey: "distance_band",
      yKeys: ["attrition_rate"],
      data: [
        { distance_band: "0-5", attrition_rate: 0.09 },
        { distance_band: "5-10", attrition_rate: 0.12 },
        { distance_band: "10-20", attrition_rate: 0.18 },
        { distance_band: "20-30", attrition_rate: 0.24 },
        { distance_band: "30-50", attrition_rate: 0.31 },
      ],
    },
    {
      id: 3,
      title: "Attrition vs Promotion Gap",
      insight: "More years since promotion corresponds to higher risk.",
      chartType: "AreaChart",
      xKey: "years_since_promo",
      yKeys: ["attrition_rate"],
      data: [
        { years_since_promo: "0", attrition_rate: 0.08 },
        { years_since_promo: "1", attrition_rate: 0.11 },
        { years_since_promo: "2", attrition_rate: 0.14 },
        { years_since_promo: "3", attrition_rate: 0.19 },
        { years_since_promo: "4", attrition_rate: 0.26 },
        { years_since_promo: "5+", attrition_rate: 0.34 },
      ],
    },
    {
      id: 4,
      title: "Attrition by Job Satisfaction",
      insight: "Low satisfaction groups carry disproportionate attrition risk.",
      chartType: "PieChart",
      xKey: "satisfaction",
      yKeys: ["attrition_rate"],
      data: [
        { satisfaction: "Very Low", attrition_rate: 0.41 },
        { satisfaction: "Low", attrition_rate: 0.28 },
        { satisfaction: "Medium", attrition_rate: 0.17 },
        { satisfaction: "High", attrition_rate: 0.09 },
        { satisfaction: "Very High", attrition_rate: 0.05 },
      ],
    },
    {
      id: 5,
      title: "Risk Drivers Comparison",
      insight: "Top factors show clear spread in relative importance.",
      chartType: "BarChart",
      xKey: "feature",
      yKeys: ["importance"],
      data: [
        { feature: "OvertimeHours", importance: 0.184 },
        { feature: "DistanceFromOffice", importance: 0.142 },
        { feature: "YearsSinceLastPromo", importance: 0.131 },
        { feature: "JobSatisfaction", importance: 0.118 },
      ],
    },
    {
      id: 6,
      title: "Protective Factors Trend",
      insight: "Higher work-life balance and tenure reduce attrition.",
      chartType: "ComposedChart",
      xKey: "factor",
      yKeys: ["attrition_rate", "retention_index"],
      data: [
        { factor: "Poor WLB", attrition_rate: 0.38, retention_index: 0.62 },
        { factor: "Fair WLB", attrition_rate: 0.22, retention_index: 0.78 },
        { factor: "Good WLB", attrition_rate: 0.14, retention_index: 0.86 },
        { factor: "Excellent WLB", attrition_rate: 0.07, retention_index: 0.93 },
      ],
    },
  ],
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

### AutoML Tournament Results

The AutoML tournament tested 3 models using 5-fold cross-validation, optimising for F1 (weighted). Gradient Boosting Classifier emerged as the winner with a score of 0.8740.

**Model Performance Leaderboard:**

| Rank | Algorithm | F1 (weighted) Score |
|------|-----------|---------------------|
| 1 | Gradient Boosting Classifier | 0.8740 |
| 2 | Random Forest Classifier | 0.8510 |
| 3 | Extra Trees Classifier | 0.8380 |

The winner outperformed the runner-up by 0.023 points, indicating a meaningful margin with stable cross-validated scores.

### Feature Importance Rankings

Importance was extracted using impurity-based feature_importances_ from the winning Gradient Boosting Classifier. OvertimeHours dominates with a relative importance nearly 30% higher than the next feature.

**Feature Importance Detailed Rankings:**

| Rank | Feature | Coefficient | Relative Importance | Directional Impact |
|------|---------|-------------|---------------------|--------------------|
| 1 | OvertimeHours | 0.184000 | 100.0% | Higher values → Higher 'Attrition' |
| 2 | DistanceFromOffice | 0.142000 | 77.2% | Higher values → Higher 'Attrition' |
| 3 | YearsSinceLastPromo | 0.131000 | 71.2% | Higher values → Higher 'Attrition' |
| 4 | JobSatisfaction | 0.118000 | 64.1% | Higher values → Lower 'Attrition' |

The top three features all relate to workplace stress and stagnation, while satisfaction acts as a protective factor.

### Stage-by-Stage Runtime Breakdown

Total pipeline time was 34.4s, with the AutoML tournament accounting for the majority of compute.

**Detailed Runtime Analysis:**

| Stage | Process | Duration (seconds) | Percentage of Total |
|-------|---------|--------------------|---------------------|
| 1 | Data Ingestion | 0.4 | 1.2% |
| 2 | Preprocessing | 1.1 | 3.2% |
| 3 | EDA | 0.8 | 2.3% |
| 4 | Task Identification | 0.2 | 0.6% |
| 5 | AutoML Tournament | 27.3 | 79.4% |
| 6 | ML Insights | 4.6 | 13.4% |
| Total | Complete Pipeline | 34.4 | 100.0% |

The AutoML tournament dominated at 79.4% of total runtime, which is expected given the cross-validated model search across multiple algorithms.
`;
