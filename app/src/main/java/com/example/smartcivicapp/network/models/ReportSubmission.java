package com.example.smartcivicapp.network.models;

import java.io.File;

/** Validated report data passed from the UI to the remote report repository. */
public final class ReportSubmission {

    private final String issueCategory;
    private final String description;
    private final double latitude;
    private final double longitude;
    private final String reportedAt;
    private final String severity;
    private final File imageFile;

    public ReportSubmission(String issueCategory, String description,
                            double latitude, double longitude, String reportedAt,
                            String severity, File imageFile) {
        this.issueCategory = issueCategory;
        this.description = description;
        this.latitude = latitude;
        this.longitude = longitude;
        this.reportedAt = reportedAt;
        this.severity = severity;
        this.imageFile = imageFile;
    }

    public String getIssueCategory() { return issueCategory; }
    public String getDescription() { return description; }
    public double getLatitude() { return latitude; }
    public double getLongitude() { return longitude; }
    public String getReportedAt() { return reportedAt; }
    public String getSeverity() { return severity; }
    public File getImageFile() { return imageFile; }
}
