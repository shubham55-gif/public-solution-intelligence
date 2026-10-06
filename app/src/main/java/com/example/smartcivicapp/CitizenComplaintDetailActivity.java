package com.example.smartcivicapp;

import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.example.smartcivicapp.database.AppDatabase;
import com.example.smartcivicapp.entities.Complaint;
import com.example.smartcivicapp.network.ReportApiService;
import com.example.smartcivicapp.network.RetrofitClient;
import com.example.smartcivicapp.network.models.RemoteReportResponse;
import com.example.smartcivicapp.utils.DateUtils;
import com.example.smartcivicapp.utils.ImageUtils;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * CitizenComplaintDetailActivity — Shows BEFORE/AFTER and resolution notes to citizen.
 * Strictly fetches fresh backend report data via authenticated JWT.
 */
public class CitizenComplaintDetailActivity extends AppCompatActivity {

    private static final String TAG = "CitizenComplaintDetail";

    private TextView tvIssue, tvStatus, tvDescription, tvResolutionNote, tvResolvedTime, tvAfterUnavailable;
    private ImageView ivBefore, ivAfter;
    private LinearLayout llResolutionInfo;

    private int localId;
    private Complaint localComplaint;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_citizen_complaint_detail);

        tvIssue             = findViewById(R.id.tvIssue);
        tvStatus            = findViewById(R.id.tvStatus);
        tvDescription       = findViewById(R.id.tvDescription);
        tvResolutionNote    = findViewById(R.id.tvResolutionNote);
        tvResolvedTime      = findViewById(R.id.tvResolvedTime);
        tvAfterUnavailable  = findViewById(R.id.tvAfterUnavailable);
        ivBefore            = findViewById(R.id.ivBefore);
        ivAfter             = findViewById(R.id.ivAfter);
        llResolutionInfo    = findViewById(R.id.llResolutionInfo);

        localId = getIntent().getIntExtra("COMPLAINT_ID", -1);
        String remoteId = getIntent().getStringExtra("EXTRA_REMOTE_ID");

        if (localId > 0) {
            localComplaint = AppDatabase.getInstance(this).complaintDao().getComplaintById(localId);
        }
        if (localComplaint == null && remoteId != null && !remoteId.isEmpty()) {
            localComplaint = AppDatabase.getInstance(this).complaintDao().getComplaintByRemoteId(remoteId);
        }

        if (localComplaint != null) {
            populateLocalData();
            if (remoteId == null || remoteId.isEmpty()) {
                remoteId = localComplaint.remoteReportId;
            }
        }

        if (remoteId != null && !remoteId.isEmpty()) {
            fetchRemoteData(remoteId);
        } else if (localComplaint == null) {
            Toast.makeText(this, "Report not found", Toast.LENGTH_SHORT).show();
            finish();
        }
    }

    private void populateLocalData() {
        if (localComplaint == null) return;
        tvIssue.setText(localComplaint.issueType != null ? localComplaint.issueType : "Report");
        tvDescription.setText(localComplaint.description != null ? localComplaint.description : "");
        
        String status = localComplaint.status;
        tvStatus.setText(status != null ? status : "Pending");
        
        if ("Resolved".equalsIgnoreCase(status)) {
            tvStatus.setText("RESOLVED ✓");
        }

        ImageUtils.loadEvidenceImage(localComplaint.beforeImagePath, ivBefore, null);
    }

    private void fetchRemoteData(String remoteId) {
        if (remoteId == null || remoteId.isEmpty()) return;

        PrefManager pref = new PrefManager(this);
        Log.d(TAG, String.format("fetchRemoteData -> reportId: %s | CurrentUser: %s | Role: %s | HasToken: %b",
                remoteId, pref.getUserId(), pref.getUserRole(), !pref.getAuthToken().isEmpty()));

        ReportApiService api = RetrofitClient.getReportApiService();
        api.getReport(remoteId).enqueue(new Callback<RemoteReportResponse>() {
            @Override
            public void onResponse(Call<RemoteReportResponse> call, Response<RemoteReportResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    Log.d(TAG, "Remote report fetch SUCCESS for reportId: " + remoteId);
                    runOnUiThread(() -> updateWithRemoteData(response.body()));
                } else {
                    String errBody = "";
                    try {
                        if (response.errorBody() != null) errBody = response.errorBody().string();
                    } catch (Exception ignored) {}
                    Log.w(TAG, String.format("Remote report fetch FAILED -> HTTP %d | %s", response.code(), errBody));
                }
            }

            @Override
            public void onFailure(Call<RemoteReportResponse> call, Throwable t) {
                Log.w(TAG, "Remote report fetch NETWORK FAILURE: " + t.getMessage());
            }
        });
    }

    private void updateWithRemoteData(RemoteReportResponse remote) {
        if (remote == null) return;

        if (remote.issue_category != null && !remote.issue_category.isEmpty()) {
            tvIssue.setText(remote.issue_category);
        }
        if (remote.description != null && !remote.description.isEmpty()) {
            tvDescription.setText(remote.description);
        }

        // Original citizen image
        if (remote.image_path != null && !remote.image_path.isEmpty()) {
            ImageUtils.loadEvidenceImage(remote.image_path, ivBefore, null);
        }

        if ("resolved".equalsIgnoreCase(remote.status)) {
            tvStatus.setText("RESOLVED ✓");
            llResolutionInfo.setVisibility(View.VISIBLE);

            if (remote.resolution_note != null && !remote.resolution_note.isEmpty()) {
                tvResolutionNote.setText(remote.resolution_note);
            } else {
                tvResolutionNote.setText("No resolution note provided.");
            }

            if (remote.resolved_at != null && !remote.resolved_at.isEmpty()) {
                String adminStr = (remote.resolved_by_admin_name != null && !remote.resolved_by_admin_name.isEmpty())
                        ? " by Admin " + remote.resolved_by_admin_name : " by Authority";
                tvResolvedTime.setText("Resolved" + adminStr + " on " + DateUtils.formatIsoTimestamp(remote.resolved_at));
            }

            // Resolution after-image
            if (remote.resolution_image_path != null && !remote.resolution_image_path.trim().isEmpty()) {
                ivAfter.setVisibility(View.VISIBLE);
                if (tvAfterUnavailable != null) tvAfterUnavailable.setVisibility(View.GONE);
                ImageUtils.loadEvidenceImage(remote.resolution_image_path, ivAfter, tvAfterUnavailable);
            } else {
                ivAfter.setVisibility(View.GONE);
                if (tvAfterUnavailable != null) tvAfterUnavailable.setVisibility(View.VISIBLE);
            }
        } else {
            llResolutionInfo.setVisibility(View.GONE);
            String st = remote.status != null ? remote.status : "Pending";
            tvStatus.setText("in_progress".equalsIgnoreCase(st) ? "IN PROGRESS" : st.toUpperCase());
        }
    }
}
