package com.example.smartcivicapp;

import android.os.Bundle;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.example.smartcivicapp.database.AppDatabase;
import com.example.smartcivicapp.database.ComplaintDao;
import com.example.smartcivicapp.database.WardCount;
import com.example.smartcivicapp.entities.Complaint;
import com.example.smartcivicapp.utils.DateUtils;

import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;

/**
 * AnalysisActivity — detailed complaint analytics screen.
 *
 * DISPLAYS:
 *  - Overall statistics (total, pending, in progress, resolved)
 *  - Average resolution time
 *  - Breakdown by issue type
 *  - Breakdown by area/ward
 *  - Repeat complaint statistics
 *  - Risk zone summary
 */
public class AnalysisActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_analysis);

        TextView tvAnalysis = findViewById(R.id.tvAnalysis);
        if (tvAnalysis != null) tvAnalysis.setText(buildAnalysisReport());
    }

    private String buildAnalysisReport() {
        ComplaintDao dao = AppDatabase.getInstance(this).complaintDao();
        List<Complaint> all = dao.getAllComplaints();

        if (all == null || all.isEmpty()) {
            return "No complaints submitted yet.\n\nData will appear here once citizens start reporting issues.";
        }

        int total      = dao.getTotalCount();
        int pending    = dao.getPendingCount();
        int inProgress = dao.getInProgressCount();
        int resolved   = dao.getResolvedCount();
        int repeats    = dao.getRepeatCount();
        long avgMs     = dao.getAvgResolutionTimeMs();

        StringBuilder sb = new StringBuilder();

        // ---- OVERVIEW ----
        sb.append("╔══════════════════════════╗\n");
        sb.append("   COMPLAINT ANALYTICS\n");
        sb.append("╚══════════════════════════╝\n\n");

        sb.append("📊 OVERVIEW\n");
        sb.append("─────────────────────────\n");
        sb.append("  Total Complaints  : ").append(total).append("\n");
        sb.append("  Pending           : ").append(pending).append("\n");
        sb.append("  In Progress       : ").append(inProgress).append("\n");
        sb.append("  Resolved          : ").append(resolved).append("\n");
        sb.append("  Repeated Issues   : ").append(repeats).append("\n");
        sb.append("  Avg Resolution    : ").append(DateUtils.formatAvgResolutionTime(avgMs)).append("\n");

        if (total > 0) {
            int resRate = (resolved * 100) / total;
            sb.append("  Resolution Rate   : ").append(resRate).append("%\n");
        }
        sb.append("\n");

        // ---- BY TYPE ----
        sb.append("📂 BY ISSUE TYPE\n");
        sb.append("─────────────────────────\n");
        String[] types = {"Road Damage", "Garbage Overflow",
                "Water Leakage", "Street Light Issue"};
        for (String t : types) {
            int cnt = dao.getCountByType(t);
            int pct = total > 0 ? (cnt * 100) / total : 0;
            String bar = buildBar(pct);
            sb.append("  ").append(padRight(t, 20))
              .append(": ").append(cnt).append(" (").append(pct).append("%)\n")
              .append("  ").append(bar).append("\n");
        }
        sb.append("\n");

        // ---- BY AREA ----
        List<WardCount> wards = dao.getWardAnalysis();
        if (!wards.isEmpty()) {
            sb.append("🗺 BY AREA / WARD\n");
            sb.append("─────────────────────────\n");
            for (WardCount wc : wards) {
                String level = wc.cnt >= 3 ? "🔴" : wc.cnt == 2 ? "🟡" : "🟢";
                sb.append("  ").append(level).append(" ")
                  .append(padRight(wc.ward, 18)).append(": ").append(wc.cnt).append(" complaints\n");
            }
            sb.append("\n");
        }

        // ---- RISK ZONES ----
        List<String> highRisk = dao.getHighRiskWards();
        if (!highRisk.isEmpty()) {
            sb.append("⚠ HIGH RISK ZONES\n");
            sb.append("─────────────────────────\n");
            for (String ward : highRisk) {
                sb.append("  • ").append(ward).append("\n");
            }
            sb.append("\n");
        }

        // ---- RECENT ----
        sb.append("🕐 RECENT COMPLAINTS\n");
        sb.append("─────────────────────────\n");
        int limit = Math.min(5, all.size());
        for (int i = 0; i < limit; i++) {
            Complaint c = all.get(i);
            sb.append("  • ").append(c.issueType)
              .append(" — ").append(c.status)
              .append(" (").append(DateUtils.timeAgo(c.createdAt)).append(")\n");
        }

        return sb.toString();
    }

    private String buildBar(int pct) {
        int filled = pct / 5; // max 20 chars
        StringBuilder bar = new StringBuilder("  [");
        for (int i = 0; i < 20; i++) bar.append(i < filled ? "█" : "░");
        bar.append("]");
        return bar.toString();
    }

    private String padRight(String s, int n) {
        return String.format("%-" + n + "s", s);
    }
}
