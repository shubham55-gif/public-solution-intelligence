package com.example.smartcivicapp.utils;

import com.example.smartcivicapp.database.AppDatabase;
import com.example.smartcivicapp.database.WardCount;
import com.example.smartcivicapp.entities.Complaint;

import android.content.Context;

import java.util.List;

/**
 * RiskAnalyzer — computes risk level and detects repeat complaints.
 */
public class RiskAnalyzer {

    public static void analyze(Context context, Complaint complaint) {
        AppDatabase db = AppDatabase.getInstance(context);

        // Find nearby complaints of the same type
        List<Complaint> nearby = db.complaintDao().getComplaintsNear(
                complaint.latitude,
                complaint.longitude,
                complaint.issueType,
                complaint.id
        );

        int nearbyCount = nearby.size();

        // Determine risk
        String risk;
        if (nearbyCount == 0)      risk = "Low";
        else if (nearbyCount == 1) risk = "Medium";
        else                       risk = "High";

        boolean isRepeat = nearbyCount > 0;

        // Update this complaint
        db.complaintDao().updateRiskAndRepeat(complaint.id, isRepeat, risk);

        // Also mark existing nearby complaints as repeats
        for (Complaint near : nearby) {
            db.complaintDao().updateRiskAndRepeat(near.id, true, "High");
        }
    }

    public static String buildDecisionReport(Context context) {
        AppDatabase db = AppDatabase.getInstance(context);

        List<WardCount> wards = db.complaintDao().getWardAnalysis();
        List<String> highRisk = db.complaintDao().getHighRiskWards();

        if (wards.isEmpty()) {
            return "No data available yet. Complaints will appear here once submitted.";
        }

        StringBuilder sb = new StringBuilder();

        if (!highRisk.isEmpty()) {
            sb.append("⚠ HIGH RISK ZONES DETECTED\n\n");
            for (String ward : highRisk) {
                sb.append("• ").append(ward).append(" — Immediate attention required\n");
            }
            sb.append("\n");
        }

        sb.append("📊 AREA-WISE SUMMARY\n\n");
        for (WardCount wc : wards) {
            String level = wc.cnt >= 3 ? "🔴 High" : wc.cnt == 2 ? "🟡 Medium" : "🟢 Low";
            sb.append("• ").append(wc.ward).append(": ")
              .append(wc.cnt).append(" complaints — ").append(level).append("\n");
        }

        return sb.toString();
    }
}
