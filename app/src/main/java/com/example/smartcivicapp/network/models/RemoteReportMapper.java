package com.example.smartcivicapp.network.models;

import com.example.smartcivicapp.entities.Complaint;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;

/** Validates and maps backend reports into the existing Room/UI complaint shape. */
public final class RemoteReportMapper {

    private RemoteReportMapper() {}

    public static List<Complaint> toComplaints(RemoteReportPage page) {
        if (page == null || page.items == null) {
            throw new IllegalArgumentException("Report list response is malformed");
        }

        if (page.items.isEmpty()) return Collections.emptyList();

        List<Complaint> complaints = new ArrayList<>(page.items.size());
        for (RemoteReportResponse remote : page.items) {
            complaints.add(toComplaint(remote));
        }
        return complaints;
    }

    public static Complaint toComplaint(RemoteReportResponse remote) {
        if (remote == null
                || isBlank(remote.id)
                || isBlank(remote.issue_category)
                || isBlank(remote.description)
                || isBlank(remote.reported_at)
                || isBlank(remote.status)
                || !Double.isFinite(remote.latitude)
                || !Double.isFinite(remote.longitude)) {
            throw new IllegalArgumentException("Report item is malformed");
        }

        long reportedAt;
        try {
            reportedAt = OffsetDateTime.parse(remote.reported_at).toInstant().toEpochMilli();
        } catch (RuntimeException exception) {
            throw new IllegalArgumentException("Report timestamp is malformed", exception);
        }

        Complaint complaint = new Complaint();
        complaint.id = 0;
        complaint.remoteReportId = remote.id;
        complaint.issueType = remote.issue_category;
        complaint.description = remote.description;
        complaint.status = displayStatus(remote.status);
        complaint.latitude = remote.latitude;
        complaint.longitude = remote.longitude;
        complaint.beforeImagePath = remote.image_path;
        complaint.createdAt = reportedAt;
        complaint.resolvedAt = 0;
        complaint.ward = "";
        complaint.citizenEmail = "";
        complaint.citizenName = "";
        complaint.timelineJson = "";
        complaint.riskLevel = (remote.severity != null && !remote.severity.isEmpty()) ? remote.severity : "Low";
        complaint.isRepeat = false;
        complaint.upvoteCount = 0;
        return complaint;
    }

    private static String displayStatus(String status) {
        String normalized = status.trim().toLowerCase(Locale.US);
        if ("pending".equals(normalized)) return "Pending";
        if ("in_progress".equals(normalized) || "in-progress".equals(normalized)) {
            return "In Progress";
        }
        if ("resolved".equals(normalized)) return "Resolved";
        throw new IllegalArgumentException("Report status is malformed");
    }

    private static boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
