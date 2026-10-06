package com.example.smartcivicapp.adapters;

import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AlertDialog;
import androidx.recyclerview.widget.RecyclerView;

import com.example.smartcivicapp.AdminComplaintDetailActivity;
import com.example.smartcivicapp.CitizenComplaintDetailActivity;
import com.example.smartcivicapp.MapsActivity;
import com.example.smartcivicapp.NotificationHelper;
import com.example.smartcivicapp.PrefManager;
import com.example.smartcivicapp.R;
import com.example.smartcivicapp.database.AppDatabase;
import com.example.smartcivicapp.entities.Complaint;
import com.example.smartcivicapp.utils.DateUtils;
import com.example.smartcivicapp.utils.TimelineHelper;
import com.example.smartcivicapp.network.models.RemoteReportResponse;
import com.example.smartcivicapp.repositories.ReportRepository;

import java.util.List;

/**
 * ComplaintAdapter — full-featured RecyclerView adapter.
 */
public class ComplaintAdapter
        extends RecyclerView.Adapter<ComplaintAdapter.ViewHolder> {

    private static final String[] STATUS_OPTIONS =
            {"Pending", "In Progress", "Resolved"};

    private final Context         context;
    private final List<Complaint> list;
    private final PrefManager     pref;
    private final ReportRepository reportRepository;
    private boolean statusUpdateInProgress;

    public ComplaintAdapter(Context context, List<Complaint> list) {
        this.context = context;
        this.list    = list;
        this.pref    = new PrefManager(context);
        this.reportRepository = new ReportRepository(context);
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(context)
                .inflate(R.layout.item_complaint, parent, false);
        return new ViewHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder h, int pos) {

        Complaint c = list.get(pos);

        // ---- Text ----
        h.tvIssue.setText(c.issueType != null ? c.issueType : "Unknown Issue");
        h.tvWard.setText(c.ward != null && !c.ward.isEmpty()
                ? "📍 " + c.ward : "📍 Location");
        h.tvTimeAgo.setText(DateUtils.timeAgo(c.createdAt));

        // ---- Type color strip + icon ----
        h.viewStrip.setBackgroundColor(getTypeColor(c.issueType));
        h.tvIcon.setText(getTypeIcon(c.issueType));

        // ---- Status chip ----
        h.tvStatus.setText(c.status);
        applyStatusStyle(h.tvStatus, c.status);

        // ---- Risk / Repeat (admin only) ----
        if (pref.isAdmin()) {
            h.layoutRiskBar.setVisibility(View.VISIBLE);
            h.tvRisk.setText(getRiskLabel(c.riskLevel));
            h.tvRisk.setTextColor(getRiskTextColor(c.riskLevel));
            h.btnUpdate.setVisibility(View.VISIBLE);

            h.tvRepeat.setVisibility(c.isRepeat ? View.VISIBLE : View.GONE);

            h.btnUpdate.setOnClickListener(v -> showStatusDialog(c, pos));

            h.itemView.setOnClickListener(v -> {
                Intent i = new Intent(context, AdminComplaintDetailActivity.class);
                i.putExtra("COMPLAINT_ID", c.id);
                if (c.remoteReportId != null && !c.remoteReportId.isEmpty()) {
                    i.putExtra(AdminComplaintDetailActivity.EXTRA_REMOTE_ID, c.remoteReportId);
                }
                i.putExtra(AdminComplaintDetailActivity.EXTRA_CATEGORY, c.issueType);
                i.putExtra(AdminComplaintDetailActivity.EXTRA_SEVERITY, c.riskLevel);
                i.putExtra(AdminComplaintDetailActivity.EXTRA_STATUS, c.status);
                i.putExtra(AdminComplaintDetailActivity.EXTRA_DESC, c.description);
                i.putExtra(AdminComplaintDetailActivity.EXTRA_LAT, c.latitude);
                i.putExtra(AdminComplaintDetailActivity.EXTRA_LNG, c.longitude);
                i.putExtra(AdminComplaintDetailActivity.EXTRA_IMAGE_PATH, c.beforeImagePath);
                i.putExtra(AdminComplaintDetailActivity.EXTRA_RESOLUTION_IMAGE_PATH, c.afterImagePath);
                if (c.createdAt > 0) {
                    i.putExtra(AdminComplaintDetailActivity.EXTRA_REPORTED_AT, String.valueOf(c.createdAt));
                }
                if (c.citizenName != null && !c.citizenName.isEmpty()) {
                    i.putExtra("REMOTE_CITIZEN_NAME", c.citizenName);
                }
                context.startActivity(i);
            });

        } else {
            h.layoutRiskBar.setVisibility(View.GONE);
            h.btnUpdate.setVisibility(View.GONE);

            h.itemView.setOnClickListener(v -> {
                Intent i = new Intent(context, CitizenComplaintDetailActivity.class);
                i.putExtra("COMPLAINT_ID", c.id);
                if (c.remoteReportId != null && !c.remoteReportId.isEmpty()) {
                    i.putExtra("EXTRA_REMOTE_ID", c.remoteReportId);
                }
                context.startActivity(i);
            });
        }
    }

    private void showStatusDialog(Complaint c, int pos) {
        if (statusUpdateInProgress) return;
        new AlertDialog.Builder(context)
                .setTitle("Update Status for:\n" + c.issueType)
                .setItems(STATUS_OPTIONS, (d, which) -> {
                    String newStatus = STATUS_OPTIONS[which];
                    statusUpdateInProgress = true;
                    Toast.makeText(context, "Updating status...", Toast.LENGTH_SHORT).show();
                    reportRepository.updateReportStatus(c.remoteReportId,
                            toRemoteStatus(newStatus),
                            new ReportRepository.StatusUpdateCallback() {
                                @Override
                                public void onSuccess(RemoteReportResponse response) {
                                    statusUpdateInProgress = false;
                                    applyLocalStatus(c, newStatus);
                                    notifyItemChanged(pos);
                                    Toast.makeText(context, "Status updated on server",
                                            Toast.LENGTH_SHORT).show();
                                }

                                @Override
                                public void onHttpError(int statusCode) {
                                    statusUpdateInProgress = false;
                                    applyLocalStatus(c, newStatus);
                                    notifyItemChanged(pos);
                                    Toast.makeText(context, "Server returned HTTP "
                                            + statusCode + ". Saved locally.",
                                            Toast.LENGTH_SHORT).show();
                                }

                                @Override
                                public void onConnectionFailure(Throwable throwable) {
                                    statusUpdateInProgress = false;
                                    applyLocalStatus(c, newStatus);
                                    notifyItemChanged(pos);
                                    Toast.makeText(context, "Server unavailable. Saved locally.",
                                            Toast.LENGTH_SHORT).show();
                                }

                                @Override
                                public void onConfigurationError(String message) {
                                    statusUpdateInProgress = false;
                                    applyLocalStatus(c, newStatus);
                                    notifyItemChanged(pos);
                                    Toast.makeText(context, "Remote update unavailable. Saved locally.",
                                            Toast.LENGTH_SHORT).show();
                                }
                            });
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void applyLocalStatus(Complaint complaint, String newStatus) {
        AppDatabase.getInstance(context).complaintDao()
                .updateStatus(complaint.id, newStatus);
        String newTimeline = TimelineHelper.appendEvent(complaint.timelineJson, newStatus);
        AppDatabase.getInstance(context).complaintDao()
                .updateTimeline(complaint.id, newTimeline);
        if ("Resolved".equalsIgnoreCase(newStatus)) {
            AppDatabase.getInstance(context).complaintDao()
                    .setResolvedAt(complaint.id, System.currentTimeMillis());
        }
        complaint.status = newStatus;
        complaint.timelineJson = newTimeline;
        NotificationHelper.showStatusUpdateNotification(
                context, complaint.id, complaint.issueType, newStatus);
    }

    private String toRemoteStatus(String status) {
        return "In Progress".equals(status) ? "in_progress" : status.toLowerCase();
    }

    // ---- Helpers ----

    private void applyStatusStyle(TextView tv, String status) {
        if ("Resolved".equalsIgnoreCase(status)) {
            tv.setTextColor(Color.parseColor("#2E7D32"));
            tv.setBackgroundResource(R.drawable.bg_status_resolved);
        } else if ("In Progress".equalsIgnoreCase(status)) {
            tv.setTextColor(Color.parseColor("#1565C0"));
            tv.setBackgroundResource(R.drawable.bg_status_inprogress);
        } else {
            tv.setTextColor(Color.parseColor("#E65100"));
            tv.setBackgroundResource(R.drawable.bg_status_pending);
        }
    }

    private int getTypeColor(String issueType) {
        if (issueType == null) return Color.parseColor("#1565C0");
        switch (issueType) {
            case "Road Damage":        return Color.parseColor("#5D4037");
            case "Garbage Overflow":   return Color.parseColor("#558B2F");
            case "Water Leakage":      return Color.parseColor("#0277BD");
            case "Street Light Issue": return Color.parseColor("#F9A825");
            default:                   return Color.parseColor("#1565C0");
        }
    }

    private String getTypeIcon(String issueType) {
        if (issueType == null) return "🔧";
        switch (issueType) {
            case "Road Damage":        return "🛣";
            case "Garbage Overflow":   return "🗑";
            case "Water Leakage":      return "💧";
            case "Street Light Issue": return "💡";
            default:                   return "🔧";
        }
    }

    private String getRiskLabel(String risk) {
        if ("High".equalsIgnoreCase(risk))   return "🔴 High Risk";
        if ("Medium".equalsIgnoreCase(risk)) return "🟡 Medium Risk";
        return "🟢 Low Risk";
    }

    private int getRiskTextColor(String risk) {
        if ("High".equalsIgnoreCase(risk))   return Color.parseColor("#C62828");
        if ("Medium".equalsIgnoreCase(risk)) return Color.parseColor("#F57C00");
        return Color.parseColor("#388E3C");
    }

    @Override
    public int getItemCount() {
        return list != null ? list.size() : 0;
    }

    // ---- ViewHolder ----
    public static class ViewHolder extends RecyclerView.ViewHolder {
        View         viewStrip;
        TextView     tvIcon, tvIssue, tvWard, tvTimeAgo,
                     tvStatus, tvRisk, tvRepeat;
        Button       btnUpdate;
        LinearLayout layoutRiskBar;

        ViewHolder(@NonNull View v) {
            super(v);
            viewStrip    = v.findViewById(R.id.viewTypeStrip);
            tvIcon       = v.findViewById(R.id.tvIssueIcon);
            tvIssue      = v.findViewById(R.id.tvIssue);
            tvWard       = v.findViewById(R.id.tvWardLabel);
            tvTimeAgo    = v.findViewById(R.id.tvTimeAgo);
            tvStatus     = v.findViewById(R.id.tvStatus);
            tvRisk       = v.findViewById(R.id.tvRiskBadge);
            tvRepeat     = v.findViewById(R.id.tvRepeatBadge);
            btnUpdate    = v.findViewById(R.id.btnUpdateStatus);
            layoutRiskBar = v.findViewById(R.id.layoutRiskBar);
        }
    }
}

