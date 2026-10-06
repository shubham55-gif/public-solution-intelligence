package com.example.smartcivicapp;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.cardview.widget.CardView;

import com.example.smartcivicapp.network.models.RemoteReportResponse;
import com.example.smartcivicapp.repositories.ReportRepository;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * AdminHomeActivity — Authority Operations Console.
 *
 * Fetches REAL data from FastAPI/PostgreSQL backend:
 *  - Live stat cards (Total / Pending / In Progress / Resolved / High Risk)
 *  - High-priority reports list with explainable risk reasons
 *  - Decision support panel built from live data
 *  - Quick access nav cards for all admin functions
 */
public class AdminHomeActivity extends AppCompatActivity {

    private PrefManager pref;
    private ReportRepository reportRepository;

    // Stat card views
    private TextView tvStatTotal, tvStatPending, tvStatProgress,
                     tvStatResolved, tvStatHighRisk, tvStatRepeats, tvStatAvgTime;

    // Decision / priority panel
    private TextView tvDecisionPanel;
    private LinearLayout llHighPriorityList;
    private ProgressBar pbLoading;
    private TextView tvLoadingStatus;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        pref = new PrefManager(this);
        if (!pref.isAdminLoggedIn()) {
            startActivity(new Intent(this, AdminLoginActivity.class));
            finish();
            return;
        }

        setContentView(R.layout.activity_admin_home);

        reportRepository = new ReportRepository(this);

        bindViews();
        setupNavCards();
        loadLiveData();
    }

    @Override
    protected void onResume() {
        super.onResume();
        loadLiveData();
    }

    private void bindViews() {
        tvStatTotal     = findViewById(R.id.tvStatTotal);
        tvStatPending   = findViewById(R.id.tvStatPending);
        tvStatProgress  = findViewById(R.id.tvStatProgress);
        tvStatResolved  = findViewById(R.id.tvStatResolved);
        tvStatHighRisk  = findViewById(R.id.tvStatHighRisk);
        tvStatRepeats   = findViewById(R.id.tvStatRepeats);
        tvStatAvgTime   = findViewById(R.id.tvStatAvgTime);
        tvDecisionPanel = findViewById(R.id.tvDecisionPanel);
        llHighPriorityList = findViewById(R.id.llHighPriorityList);
        pbLoading        = findViewById(R.id.pbAdminLoading);
        tvLoadingStatus  = findViewById(R.id.tvLoadingStatus);
    }

    // ── Live Data ──────────────────────────────────────────────────────────────

    private void loadLiveData() {
        showLoading(true);

        reportRepository.getAllReports(new ReportRepository.AdminReportListCallback() {
            @Override
            public void onSuccess(List<RemoteReportResponse> reports, int total) {
                runOnUiThread(() -> {
                    showLoading(false);
                    populateStats(reports, total);
                    populateDecisionPanel(reports);
                    populateHighPriorityList(reports);
                });
            }

            @Override
            public void onHttpError(int statusCode) {
                runOnUiThread(() -> {
                    showLoading(false);
                    showError("Server error " + statusCode + ". Check backend connection.");
                });
            }

            @Override
            public void onFailure(Throwable throwable) {
                runOnUiThread(() -> {
                    showLoading(false);
                    showError("Network unavailable. Cannot reach FastAPI.");
                });
            }

            @Override
            public void onConfigurationError(String message) {
                runOnUiThread(() -> {
                    showLoading(false);
                    showError("Configuration error: " + message);
                });
            }
        });
    }

    // ── Statistics ─────────────────────────────────────────────────────────────

    private void populateStats(List<RemoteReportResponse> reports, int total) {
        int pending = 0, inProgress = 0, resolved = 0, highRisk = 0;

        for (RemoteReportResponse r : reports) {
            String s = r.status != null ? r.status.toLowerCase(Locale.US) : "";
            if ("pending".equals(s)) pending++;
            else if ("in_progress".equals(s) || "in-progress".equals(s)) inProgress++;
            else if ("resolved".equals(s)) resolved++;

            String sev = r.severity != null ? r.severity.toLowerCase(Locale.US) : "";
            if ("high".equals(sev) || "critical".equals(sev)) highRisk++;
        }

        int displayTotal = total > 0 ? total : reports.size();

        setText(tvStatTotal,    String.valueOf(displayTotal));
        setText(tvStatPending,  String.valueOf(pending));
        setText(tvStatProgress, String.valueOf(inProgress));
        setText(tvStatResolved, String.valueOf(resolved));
        setText(tvStatHighRisk, String.valueOf(highRisk));

        // Repeat: reports with more than one matching category in same severity
        int repeats = countRepeatedCategories(reports);
        setText(tvStatRepeats, String.valueOf(repeats));

        // Avg time: placeholder derived from resolved count (real metric needs timestamps)
        if (resolved > 0) {
            setText(tvStatAvgTime, resolved + " done");
        } else {
            setText(tvStatAvgTime, "N/A");
        }
    }

    /** Counts categories that appear more than once across all reports (rough repeat proxy). */
    private int countRepeatedCategories(List<RemoteReportResponse> reports) {
        android.util.ArrayMap<String, Integer> counts = new android.util.ArrayMap<>();
        for (RemoteReportResponse r : reports) {
            if (r.issue_category != null) {
                int c = counts.getOrDefault(r.issue_category, 0);
                counts.put(r.issue_category, c + 1);
            }
        }
        int repeated = 0;
        for (int count : counts.values()) {
            if (count > 1) repeated += count;
        }
        return repeated;
    }

    // ── Decision Support Panel ─────────────────────────────────────────────────

    private void populateDecisionPanel(List<RemoteReportResponse> reports) {
        if (tvDecisionPanel == null) return;
        if (reports.isEmpty()) {
            tvDecisionPanel.setText("No reports found. System is clear.");
            return;
        }

        int pending = 0, highRisk = 0;
        android.util.ArrayMap<String, Integer> categoryCount = new android.util.ArrayMap<>();

        for (RemoteReportResponse r : reports) {
            String s = r.status != null ? r.status.toLowerCase(Locale.US) : "";
            if ("pending".equals(s)) pending++;

            String sev = r.severity != null ? r.severity.toLowerCase(Locale.US) : "";
            if ("high".equals(sev) || "critical".equals(sev)) highRisk++;

            if (r.issue_category != null) {
                int c = categoryCount.getOrDefault(r.issue_category, 0);
                categoryCount.put(r.issue_category, c + 1);
            }
        }

        // Find dominant category
        String topCategory = "Unknown";
        int topCount = 0;
        for (String cat : categoryCount.keySet()) {
            int c = categoryCount.get(cat);
            if (c > topCount) { topCount = c; topCategory = cat; }
        }

        StringBuilder sb = new StringBuilder();
        sb.append("📊 LIVE INTELLIGENCE SUMMARY\n");
        sb.append("─────────────────────────────\n");
        sb.append("Total reports in system: ").append(reports.size()).append("\n");
        if (pending > 0) {
            sb.append("⚠ ").append(pending).append(" report(s) need IMMEDIATE attention (Pending)\n");
        }
        if (highRisk > 0) {
            sb.append("🔴 ").append(highRisk).append(" HIGH RISK report(s) detected\n");
        }
        sb.append("📍 Most reported issue: ").append(topCategory)
          .append(" (").append(topCount).append(" reports)\n");
        sb.append("\n💡 RECOMMENDED ACTIONS:\n");
        if (highRisk > 0) {
            sb.append("• Dispatch field team for HIGH severity reports\n");
        }
        if (pending > 0) {
            sb.append("• Review ").append(pending).append(" pending report(s) immediately\n");
        }
        sb.append("• Monitor ").append(topCategory).append(" cluster for hotspot formation");

        tvDecisionPanel.setText(sb.toString());
    }

    // ── High Priority List ─────────────────────────────────────────────────────

    private void populateHighPriorityList(List<RemoteReportResponse> reports) {
        if (llHighPriorityList == null) return;
        llHighPriorityList.removeAllViews();

        // Filter high-risk + pending reports for the priority list
        List<RemoteReportResponse> priority = new ArrayList<>();
        for (RemoteReportResponse r : reports) {
            String sev = r.severity != null ? r.severity.toLowerCase(Locale.US) : "";
            String s   = r.status   != null ? r.status.toLowerCase(Locale.US)   : "";
            boolean isHigh    = "high".equals(sev) || "critical".equals(sev);
            boolean isPending = "pending".equals(s);
            if (isHigh || isPending) priority.add(r);
        }

        if (priority.isEmpty()) {
            TextView tv = new TextView(this);
            tv.setText("✅ No high-priority or pending reports right now.");
            tv.setTextSize(13f);
            tv.setPadding(0, 8, 0, 0);
            tv.setTextColor(getResources().getColor(R.color.textSecondary, getTheme()));
            llHighPriorityList.addView(tv);
            return;
        }

        int shown = 0;
        for (RemoteReportResponse r : priority) {
            if (shown++ >= 8) break; // show top 8
            llHighPriorityList.addView(buildPriorityCard(r));
        }
    }

    private View buildPriorityCard(RemoteReportResponse r) {
        // Build a compact summary card programmatically
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.VERTICAL);
        row.setPadding(0, 8, 0, 8);

        // Category + status line
        String sev = r.severity != null ? r.severity : "Unknown";
        String status = r.status != null ? r.status : "unknown";
        String cat = r.issue_category != null ? r.issue_category : "Unknown";

        String riskEmoji = "high".equalsIgnoreCase(sev) || "critical".equalsIgnoreCase(sev)
                ? "🔴" : "🟡";

        TextView tvHeader = new TextView(this);
        tvHeader.setText(riskEmoji + " " + cat + "  •  " + displayStatus(status));
        tvHeader.setTextSize(13f);
        tvHeader.setTextColor(getResources().getColor(R.color.textPrimary, getTheme()));
        tvHeader.setTypeface(null, android.graphics.Typeface.BOLD);

        // Description snippet
        String desc = r.description != null && !r.description.isEmpty()
                ? r.description : "No description";
        if (desc.length() > 80) desc = desc.substring(0, 80) + "…";

        TextView tvDesc = new TextView(this);
        tvDesc.setText("  " + desc);
        tvDesc.setTextSize(12f);
        tvDesc.setTextColor(getResources().getColor(R.color.textSecondary, getTheme()));

        // Explainable reason
        String reason = buildExplainableReason(r);
        TextView tvReason = new TextView(this);
        tvReason.setText("  📌 " + reason);
        tvReason.setTextSize(11f);
        tvReason.setTextColor(0xFF6A1B9A); // purple accent

        // Separator line
        View divider = new View(this);
        LinearLayout.LayoutParams dp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 1);
        dp.topMargin = 8;
        divider.setLayoutParams(dp);
        divider.setBackgroundColor(getResources().getColor(R.color.divider, getTheme()));

        // Click → open complaint detail (pass remoteId as string extra)
        row.setClickable(true);
        row.setFocusable(true);
        row.setOnClickListener(v -> {
            Intent i = new Intent(this, AdminComplaintDetailActivity.class);
            i.putExtra("REMOTE_REPORT_ID", r.id);
            i.putExtra("REMOTE_CATEGORY",  r.issue_category);
            i.putExtra("REMOTE_SEVERITY",  r.severity);
            i.putExtra("REMOTE_STATUS",    r.status);
            i.putExtra("REMOTE_DESC",      r.description);
            i.putExtra("REMOTE_LAT",       r.latitude);
            i.putExtra("REMOTE_LNG",       r.longitude);
            i.putExtra("REMOTE_REPORTED_AT", r.reported_at);
            i.putExtra("REMOTE_IMAGE_PATH",  r.image_path);
            i.putExtra("REMOTE_CITIZEN_NAME", r.citizen_name);
            i.putExtra("ASSIGNED_ADMIN_NAME", r.assigned_admin_name);
            i.putExtra("RESOLVED_BY_ADMIN_NAME", r.resolved_by_admin_name);
            i.putExtra("RESOLVED_AT", r.resolved_at);
            i.putExtra("RESOLUTION_NOTE", r.resolution_note);
            i.putExtra("RESOLUTION_IMAGE_PATH", r.resolution_image_path);
            i.putExtra("HAS_AI_ANALYSIS",    r.has_ai_analysis);
            startActivity(i);
        });

        row.addView(tvHeader);
        row.addView(tvDesc);
        row.addView(tvReason);
        row.addView(divider);
        return row;
    }

    private String buildExplainableReason(RemoteReportResponse r) {
        String sev = r.severity != null ? r.severity : "low";
        String s   = r.status   != null ? r.status   : "pending";
        StringBuilder sb = new StringBuilder();

        if ("high".equalsIgnoreCase(sev) || "critical".equalsIgnoreCase(sev)) {
            sb.append("High severity reported by citizen. ");
        }
        if ("pending".equalsIgnoreCase(s)) {
            sb.append("No authority action taken yet. ");
        }
        if (r.has_ai_analysis) {
            sb.append("AI evidence available for review.");
        } else {
            sb.append("AI analysis pending.");
        }
        return sb.toString().trim();
    }

    private String displayStatus(String raw) {
        if (raw == null) return "Unknown";
        switch (raw.toLowerCase(Locale.US)) {
            case "pending":    return "Pending";
            case "in_progress":
            case "in-progress": return "In Progress";
            case "resolved":   return "Resolved";
            default:           return raw;
        }
    }

    // ── Nav Cards ──────────────────────────────────────────────────────────────

    private void setupNavCards() {
        CardView cardComplaints = findViewById(R.id.cardManageComplaints);
        if (cardComplaints != null) {
            cardComplaints.setOnClickListener(v ->
                    startActivity(new Intent(this, ComplaintListActivity.class)));
        }

        CardView cardMap = findViewById(R.id.cardMap);
        if (cardMap != null) {
            cardMap.setOnClickListener(v ->
                    startActivity(new Intent(this, MapsActivity.class)));
        }

        CardView cardAnalysis = findViewById(R.id.cardAnalysis);
        if (cardAnalysis != null) {
            cardAnalysis.setOnClickListener(v ->
                    startActivity(new Intent(this, AnalysisActivity.class)));
        }

        CardView cardRisk = findViewById(R.id.cardRiskZones);
        if (cardRisk != null) {
            cardRisk.setOnClickListener(v ->
                    startActivity(new Intent(this, RiskZonesActivity.class)));
        }

        TextView tvLogout = findViewById(R.id.tvLogout);
        if (tvLogout != null) {
            tvLogout.setOnClickListener(v -> {
                pref.logout();
                Intent intent = new Intent(this, RoleSelectionActivity.class);
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                startActivity(intent);
                finish();
            });
        }
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    private void showLoading(boolean loading) {
        if (pbLoading != null)       pbLoading.setVisibility(loading ? View.VISIBLE : View.GONE);
        if (tvLoadingStatus != null) tvLoadingStatus.setVisibility(loading ? View.VISIBLE : View.GONE);
    }

    private void showError(String msg) {
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show();
        if (tvDecisionPanel != null) tvDecisionPanel.setText("⚠ " + msg);
    }

    private void setText(TextView tv, String text) {
        if (tv != null) tv.setText(text);
    }
}
