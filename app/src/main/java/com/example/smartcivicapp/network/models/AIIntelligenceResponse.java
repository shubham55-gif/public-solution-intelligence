package com.example.smartcivicapp.network.models;

import java.util.List;

/**
 * Gson model for the FastAPI UnifiedReportIntelligenceResponse.
 * Maps: GET/POST /api/v1/ai/analyze-report/{report_id}
 */
public class AIIntelligenceResponse {

    public String report_id;
    public String issue_category;
    public boolean analysis_available;
    public TextAnalysis text_analysis;
    public ImageAnalysis image_analysis;
    public boolean overall_needs_review;
    public EvidenceConsistency evidence_consistency;
    public String explanation;

    // Pass 3 Extended Intelligence
    public DuplicateInfo duplicate;
    public SpatialInfo spatial;
    public TemporalInfo temporal;
    public RecurrenceInfo recurrence;
    public TrendInfo trend;
    public String severity; // "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    public RiskInfo risk;
    public String priority; // "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    public List<String> priority_reasons;
    public RecommendationInfo recommendation;

    public static class TextAnalysis {
        public boolean available;
        public String summary;
        public List<String> keywords;
        public boolean category_consistent;
        public List<String> urgency_indicators;
        public List<String> hazard_indicators;
        public float confidence;
        public boolean needs_review;
        public String explanation;
    }

    public static class ImageAnalysis {
        public boolean available;
        public String validation_result; // "YES" | "NO" | "UNCERTAIN"
        public boolean image_consistent;
        public float confidence;
        public boolean needs_review;
        public String explanation;
    }

    public static class EvidenceConsistency {
        public boolean text_category_consistent;
        public Boolean image_category_consistent; // nullable
        public Boolean agreement;                 // nullable
        public String consistency_status;         // "CONSISTENT" | "INCONSISTENT" | "UNCERTAIN"
    }

    public static class DuplicateInfo {
        public boolean is_duplicate;
        public String duplicate_report_id;
        public String duplicate_reason;
        public Double duplicate_distance;
        public Double duplicate_time_difference;
    }

    public static class SpatialInfo {
        public String cluster_id;
        public Integer cluster_size;
        public Double cluster_center_latitude;
        public Double cluster_center_longitude;
        public Double cluster_radius_meters;
        public boolean is_hotspot;
    }

    public static class TemporalInfo {
        public int recent_report_count;
        public String time_window;
        public String recent_activity;
        public String temporal_concentration;
    }

    public static class RecurrenceInfo {
        public boolean is_recurring;
        public int recurrence_count;
        public String recurrence_window;
        public String recurrence_reason;
    }

    public static class TrendInfo {
        public String trend; // "INCREASING" | "STABLE" | "DECREASING" | "UNKNOWN"
        public int current_count;
        public int baseline_count;
    }

    public static class RiskInfo {
        public float risk_score;
        public String risk_level; // "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
        public List<String> risk_factors;
    }

    public static class RecommendationInfo {
        public String recommended_action;
        public String action_type;
        public String reason;
        public boolean is_available;
    }
}
