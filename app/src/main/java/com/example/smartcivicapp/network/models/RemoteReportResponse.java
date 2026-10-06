package com.example.smartcivicapp.network.models;

/** Gson model for the FastAPI report-creation response. */
public class RemoteReportResponse {
    public String id;
    public String user_id;
    public String citizen_name;
    public String issue_category;
    public String description;
    public double latitude;
    public double longitude;
    public String reported_at;
    public String severity;
    public String status;
    public String image_path;
    public String resolution_image_path;
    public String resolution_note;
    public String resolved_at;
    public String assigned_admin_id;
    public String assigned_admin_name;
    public String resolved_by_admin_id;
    public String resolved_by_admin_name;
    public boolean has_ai_analysis;
    public String created_at;
    public String updated_at;
    public java.util.List<StatusHistoryItem> status_history;

    public static class StatusHistoryItem {
        public String old_status;
        public String new_status;
        public String changed_by_admin_name;
        public String note;
        public String changed_at;
    }
}
