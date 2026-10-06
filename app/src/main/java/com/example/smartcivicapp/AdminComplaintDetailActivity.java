package com.example.smartcivicapp;

import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.os.Bundle;
import android.provider.MediaStore;
import android.util.Log;
import android.view.View;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AlertDialog;
import androidx.appcompat.app.AppCompatActivity;
import androidx.cardview.widget.CardView;

import com.google.android.material.button.MaterialButton;
import com.example.smartcivicapp.network.ReportApiService;
import com.example.smartcivicapp.network.RetrofitClient;
import com.example.smartcivicapp.network.models.AIIntelligenceResponse;
import com.example.smartcivicapp.network.models.RemoteReportResponse;
import com.example.smartcivicapp.repositories.ReportRepository;
import com.example.smartcivicapp.utils.DateUtils;
import com.example.smartcivicapp.utils.ImageUtils;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.List;
import java.util.Locale;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * AdminComplaintDetailActivity — Full Authority Operations Intelligence Console.
 *
 * Receives report data from AdminHomeActivity as Intent extras (remote API data).
 * Live-syncs with FastAPI GET /api/v1/reports/{report_id} and GET /api/v1/ai/analyze-report/{report_id}.
 */
public class AdminComplaintDetailActivity extends AppCompatActivity {

    private static final String TAG = "AdminComplaintDetail";

    // ── Intent extra keys ──
    public static final String EXTRA_REMOTE_ID             = "REMOTE_REPORT_ID";
    public static final String EXTRA_CATEGORY              = "REMOTE_CATEGORY";
    public static final String EXTRA_SEVERITY              = "REMOTE_SEVERITY";
    public static final String EXTRA_STATUS                = "REMOTE_STATUS";
    public static final String EXTRA_DESC                  = "REMOTE_DESC";
    public static final String EXTRA_LAT                   = "REMOTE_LAT";
    public static final String EXTRA_LNG                   = "REMOTE_LNG";
    public static final String EXTRA_REPORTED_AT           = "REMOTE_REPORTED_AT";
    public static final String EXTRA_IMAGE_PATH            = "REMOTE_IMAGE_PATH";
    public static final String EXTRA_RESOLUTION_IMAGE_PATH = "RESOLUTION_IMAGE_PATH";
    public static final String EXTRA_HAS_AI                = "HAS_AI_ANALYSIS";

    // ── Report fields ──
    private String remoteReportId;
    private String category;
    private String severity;
    private String currentStatus;
    private String description;
    private double latitude;
    private double longitude;
    private String reportedAt;
    private String imagePath;
    private String resolutionImagePath;
    private String citizenName, assignedAdminName, resolvedByAdminName, resolvedAt, resolutionNote;
    private List<RemoteReportResponse.StatusHistoryItem> statusHistoryList;

    // ── Local Room fallback ──
    private com.example.smartcivicapp.entities.Complaint localComplaint;

    // ── Views ──
    private TextView tvIssue, tvStatus, tvRisk, tvDesc, tvWard, tvCreated,
                     tvCitizen, tvAssignedAdmin, tvTimeline, tvRepeat;
    private TextView tvAiSummary, tvAiKeywords, tvAiUrgency, tvAiHazard,
                     tvAiConfidence, tvAiImageResult, tvAiExplanation;
    private LinearLayout llAiPanel;
    private ProgressBar pbAiLoading;
    private ImageView ivBefore, ivAfter;
    private TextView tvAfterUnavailable;
    private MaterialButton btnUpdateStatus, btnMap, btnUploadAfter, btnFetchAI, btnResolveReport;
    private CardView cardResolvedSummary;
    private LinearLayout llResolutionControls;
    private TextView tvResolvedBy, tvResolvedAt, tvResolutionNoteText;
    private com.google.android.material.textfield.TextInputEditText etResolutionNote;
    private File currentAfterImageFile;

    // ── Repo ──
    private ReportRepository reportRepository;
    private boolean statusUpdating = false;

    private final ActivityResultLauncher<Intent> cameraLauncher =
            registerForActivityResult(
                    new ActivityResultContracts.StartActivityForResult(),
                    result -> {
                        if (result.getResultCode() == RESULT_OK
                                && result.getData() != null
                                && result.getData().getExtras() != null) {
                            Bitmap bmp = (Bitmap) result.getData().getExtras().get("data");
                            if (bmp != null) saveAfterImage(bmp);
                        }
                    });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_admin_complaint_detail);

        reportRepository = new ReportRepository(this);

        // Read intent extras
        Intent intent = getIntent();
        remoteReportId      = intent.getStringExtra(EXTRA_REMOTE_ID);
        category            = intent.getStringExtra(EXTRA_CATEGORY);
        severity            = intent.getStringExtra(EXTRA_SEVERITY);
        currentStatus       = intent.getStringExtra(EXTRA_STATUS);
        description         = intent.getStringExtra(EXTRA_DESC);
        latitude            = intent.getDoubleExtra(EXTRA_LAT, 0.0);
        longitude           = intent.getDoubleExtra(EXTRA_LNG, 0.0);
        reportedAt          = intent.getStringExtra(EXTRA_REPORTED_AT);
        imagePath           = intent.getStringExtra(EXTRA_IMAGE_PATH);
        resolutionImagePath = intent.getStringExtra(EXTRA_RESOLUTION_IMAGE_PATH);
        citizenName         = intent.getStringExtra("REMOTE_CITIZEN_NAME");
        assignedAdminName   = intent.getStringExtra("ASSIGNED_ADMIN_NAME");
        resolvedByAdminName = intent.getStringExtra("RESOLVED_BY_ADMIN_NAME");
        resolvedAt          = intent.getStringExtra("RESOLVED_AT");
        resolutionNote      = intent.getStringExtra("RESOLUTION_NOTE");

        // Fallback: if opened with a Room COMPLAINT_ID
        int localId = intent.getIntExtra("COMPLAINT_ID", -1);
        if (localId != -1) {
            loadFromRoom(localId);
        }

        bindViews();
        populateHeader();
        populateInfoCard();
        populateBeforeImage();
        populateAfterImage();
        updateResolutionUI();
        populateTimeline();
        setupButtons();

        // Fetch fresh remote data from backend for full accountability & timeline
        if (remoteReportId != null && !remoteReportId.isEmpty()) {
            fetchRemoteReportDetails();
            fetchAIIntelligence();
        }
    }

    // ── Room fallback ─────────────────────────────────────────────────────────

    private void loadFromRoom(int localId) {
        com.example.smartcivicapp.database.ComplaintDao dao =
                com.example.smartcivicapp.database.AppDatabase.getInstance(this).complaintDao();
        localComplaint = dao.getComplaintById(localId);
        if (localComplaint == null) return;

        if (remoteReportId == null || remoteReportId.isEmpty()) {
            remoteReportId = localComplaint.remoteReportId;
        }
        if (category == null) category = localComplaint.issueType;
        if (severity == null) severity = localComplaint.riskLevel;
        if (currentStatus == null) currentStatus = localComplaint.status;
        if (description == null) description = localComplaint.description;
        if (latitude == 0.0) latitude = localComplaint.latitude;
        if (longitude == 0.0) longitude = localComplaint.longitude;
        if (imagePath == null) imagePath = localComplaint.beforeImagePath;
        if (resolutionImagePath == null) resolutionImagePath = localComplaint.afterImagePath;
        if (reportedAt == null && localComplaint.createdAt > 0) {
            reportedAt = String.valueOf(localComplaint.createdAt);
        }
    }

    // ── View binding ──────────────────────────────────────────────────────────

    private void bindViews() {
        tvIssue             = findViewById(R.id.tvIssue);
        tvStatus            = findViewById(R.id.tvStatus);
        tvRisk              = findViewById(R.id.tvRisk);
        tvDesc              = findViewById(R.id.tvDesc);
        tvWard              = findViewById(R.id.tvWard);
        tvCreated           = findViewById(R.id.tvCreated);
        tvCitizen           = findViewById(R.id.tvCitizen);
        tvAssignedAdmin     = findViewById(R.id.tvAssignedAdmin);
        tvRepeat            = findViewById(R.id.tvRepeat);
        tvTimeline          = findViewById(R.id.tvTimeline);

        // AI Intelligence panel
        llAiPanel           = findViewById(R.id.llAiPanel);
        pbAiLoading         = findViewById(R.id.pbAiLoading);
        tvAiSummary         = findViewById(R.id.tvAiSummary);
        tvAiKeywords        = findViewById(R.id.tvAiKeywords);
        tvAiUrgency         = findViewById(R.id.tvAiUrgency);
        tvAiHazard          = findViewById(R.id.tvAiHazard);
        tvAiConfidence      = findViewById(R.id.tvAiConfidence);
        tvAiImageResult     = findViewById(R.id.tvAiImageResult);
        tvAiExplanation     = findViewById(R.id.tvAiExplanation);

        ivBefore            = findViewById(R.id.ivBefore);
        ivAfter             = findViewById(R.id.ivAfter);
        tvAfterUnavailable  = findViewById(R.id.tvAfterUnavailable);

        cardResolvedSummary = findViewById(R.id.cardResolvedSummary);
        llResolutionControls= findViewById(R.id.llResolutionControls);
        tvResolvedBy        = findViewById(R.id.tvResolvedBy);
        tvResolvedAt        = findViewById(R.id.tvResolvedAt);
        tvResolutionNoteText= findViewById(R.id.tvResolutionNoteText);

        btnUpdateStatus     = findViewById(R.id.btnUpdateStatus);
        btnMap              = findViewById(R.id.btnMap);
        btnUploadAfter      = findViewById(R.id.btnUploadAfter);
        btnFetchAI          = findViewById(R.id.btnFetchAI);
        btnResolveReport    = findViewById(R.id.btnResolveReport);
        etResolutionNote    = findViewById(R.id.etResolutionNote);
    }

    // ── Header ────────────────────────────────────────────────────────────────

    private void populateHeader() {
        if (tvIssue != null) tvIssue.setText(category != null ? category : "Unknown Issue");
        if (tvStatus != null) {
            tvStatus.setText(displayStatus(currentStatus));
            applyStatusChipColor(tvStatus, currentStatus);
        }
        if (tvRisk != null) {
            String sev = severity != null ? severity : "Unknown";
            String emoji = "high".equalsIgnoreCase(sev) || "critical".equalsIgnoreCase(sev)
                    ? "🔴" : ("medium".equalsIgnoreCase(sev) ? "🟡" : "🟢");
            tvRisk.setText(emoji + " " + sev.toUpperCase(Locale.US) + " RISK");
            if ("high".equalsIgnoreCase(sev) || "critical".equalsIgnoreCase(sev)) {
                tvRisk.setTextColor(Color.parseColor("#FFCDD2"));
            } else if ("medium".equalsIgnoreCase(sev)) {
                tvRisk.setTextColor(Color.parseColor("#FFE082"));
            } else {
                tvRisk.setTextColor(Color.parseColor("#C8E6C9"));
            }
        }
        if (tvRepeat != null) tvRepeat.setVisibility(View.GONE);
    }

    private void applyStatusChipColor(TextView chip, String status) {
        if (chip == null || status == null) return;
        String s = status.toLowerCase(Locale.US);
        if ("resolved".equals(s)) {
            chip.setTextColor(Color.parseColor("#2E7D32"));
        } else if ("in_progress".equals(s) || "in-progress".equals(s)) {
            chip.setTextColor(Color.parseColor("#1565C0"));
        } else {
            chip.setTextColor(Color.parseColor("#E65100"));
        }
    }

    // ── Info card ─────────────────────────────────────────────────────────────

    private void populateInfoCard() {
        if (tvDesc != null) {
            tvDesc.setText(description != null && !description.isEmpty()
                    ? description : "No description provided.");
        }
        if (tvWard != null) {
            tvWard.setText("Lat " + String.format(Locale.US, "%.5f", latitude)
                    + ",  Lng " + String.format(Locale.US, "%.5f", longitude));
        }
        if (tvCreated != null) {
            tvCreated.setText(DateUtils.formatIsoTimestamp(reportedAt));
        }
        if (tvCitizen != null) {
            String name = (citizenName != null && !citizenName.isEmpty())
                    ? citizenName : (localComplaint != null && localComplaint.citizenName != null && !localComplaint.citizenName.isEmpty()
                    ? localComplaint.citizenName : "Citizen");
            tvCitizen.setText(name);
        }
        if (tvAssignedAdmin != null) {
            if (assignedAdminName != null && !assignedAdminName.isEmpty()) {
                tvAssignedAdmin.setText("Admin " + assignedAdminName);
            } else {
                tvAssignedAdmin.setText("Unassigned");
            }
        }
    }

    // ── Fetch Remote Report Details (Accountability + Status History) ─────────

    private void fetchRemoteReportDetails() {
        if (remoteReportId == null || remoteReportId.isEmpty()) return;

        ReportApiService api = RetrofitClient.getReportApiService();
        api.getReport(remoteReportId).enqueue(new Callback<RemoteReportResponse>() {
            @Override
            public void onResponse(Call<RemoteReportResponse> call, Response<RemoteReportResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    RemoteReportResponse r = response.body();
                    runOnUiThread(() -> {
                        if (r.issue_category != null) category = r.issue_category;
                        if (r.severity != null) severity = r.severity;
                        if (r.status != null) currentStatus = r.status;
                        if (r.description != null) description = r.description;
                        if (r.latitude != 0.0) latitude = r.latitude;
                        if (r.longitude != 0.0) longitude = r.longitude;
                        if (r.reported_at != null) reportedAt = r.reported_at;
                        if (r.image_path != null) imagePath = r.image_path;
                        if (r.resolution_image_path != null) resolutionImagePath = r.resolution_image_path;
                        if (r.citizen_name != null) citizenName = r.citizen_name;
                        if (r.assigned_admin_name != null) assignedAdminName = r.assigned_admin_name;
                        if (r.resolved_by_admin_name != null) resolvedByAdminName = r.resolved_by_admin_name;
                        if (r.resolved_at != null) resolvedAt = r.resolved_at;
                        if (r.resolution_note != null) resolutionNote = r.resolution_note;
                        if (r.status_history != null) statusHistoryList = r.status_history;

                        populateHeader();
                        populateInfoCard();
                        populateBeforeImage();
                        populateAfterImage();
                        updateResolutionUI();
                        populateTimeline();
                    });
                }
            }

            @Override
            public void onFailure(Call<RemoteReportResponse> call, Throwable t) {
                Log.w(TAG, "Failed to fetch remote report details: " + t.getMessage());
            }
        });
    }

    // ── Evidence Images & Resolution State ────────────────────────────────────

    private void populateBeforeImage() {
        ImageUtils.loadEvidenceImage(imagePath, ivBefore, null);
    }

    private void populateAfterImage() {
        String after = (resolutionImagePath != null && !resolutionImagePath.trim().isEmpty())
                ? resolutionImagePath
                : (localComplaint != null ? localComplaint.afterImagePath : null);

        boolean isResolved = "resolved".equalsIgnoreCase(currentStatus);
        if (after != null && !after.trim().isEmpty()) {
            if (ivAfter != null) ivAfter.setVisibility(View.VISIBLE);
            if (tvAfterUnavailable != null) tvAfterUnavailable.setVisibility(View.GONE);
            ImageUtils.loadEvidenceImage(after, ivAfter, tvAfterUnavailable);
        } else {
            if (ivAfter != null) {
                ivAfter.setImageResource(R.drawable.bg_image_placeholder);
                ivAfter.setVisibility(isResolved ? View.GONE : View.VISIBLE);
            }
            if (tvAfterUnavailable != null) {
                tvAfterUnavailable.setVisibility(isResolved ? View.VISIBLE : View.GONE);
            }
        }
    }

    private void updateResolutionUI() {
        boolean isResolved = "resolved".equalsIgnoreCase(currentStatus);

        if (isResolved) {
            // Read-only resolved section
            if (cardResolvedSummary != null) cardResolvedSummary.setVisibility(View.VISIBLE);
            if (llResolutionControls != null) llResolutionControls.setVisibility(View.GONE);
            if (btnUpdateStatus != null) {
                btnUpdateStatus.setEnabled(false);
                btnUpdateStatus.setText("Status: Resolved ✓");
            }

            if (tvResolvedBy != null) {
                String admin = (resolvedByAdminName != null && !resolvedByAdminName.isEmpty())
                        ? "Admin " + resolvedByAdminName : "Authority";
                tvResolvedBy.setText("Resolved By: " + admin);
            }

            if (tvResolvedAt != null) {
                tvResolvedAt.setText("Resolved At: " + DateUtils.formatIsoTimestamp(resolvedAt));
            }

            if (tvResolutionNoteText != null) {
                tvResolutionNoteText.setText(resolutionNote != null && !resolutionNote.trim().isEmpty()
                        ? resolutionNote : "No resolution note provided.");
            }

            // After photo availability check
            String after = (resolutionImagePath != null && !resolutionImagePath.trim().isEmpty())
                    ? resolutionImagePath
                    : (localComplaint != null ? localComplaint.afterImagePath : null);
            if (tvAfterUnavailable != null) {
                tvAfterUnavailable.setVisibility((after == null || after.trim().isEmpty()) ? View.VISIBLE : View.GONE);
            }
            if (ivAfter != null) {
                ivAfter.setVisibility((after != null && !after.trim().isEmpty()) ? View.VISIBLE : View.GONE);
            }

        } else {
            // Editable resolution controls
            if (cardResolvedSummary != null) cardResolvedSummary.setVisibility(View.GONE);
            if (llResolutionControls != null) llResolutionControls.setVisibility(View.VISIBLE);
            if (tvAfterUnavailable != null) tvAfterUnavailable.setVisibility(View.GONE);
            if (ivAfter != null) ivAfter.setVisibility(View.VISIBLE);
            if (btnUpdateStatus != null) {
                btnUpdateStatus.setEnabled(true);
                btnUpdateStatus.setText("Update Status");
            }
        }
    }

    // ── Timeline ──────────────────────────────────────────────────────────────

    private void populateTimeline() {
        if (tvTimeline == null) return;
        StringBuilder sb = new StringBuilder();

        // 1. Initial report submission
        sb.append("📅 Report Submitted\n");
        sb.append("   ").append(DateUtils.formatIsoTimestamp(reportedAt)).append("\n\n");

        // 2. Structured events from backend status history
        if (statusHistoryList != null && !statusHistoryList.isEmpty()) {
            for (RemoteReportResponse.StatusHistoryItem item : statusHistoryList) {
                String newStatus = item.new_status != null ? item.new_status.toLowerCase(Locale.US) : "";
                String admin = item.changed_by_admin_name != null && !item.changed_by_admin_name.isEmpty()
                        ? "Admin " + item.changed_by_admin_name : "Authority";

                if ("resolved".equals(newStatus)) {
                    sb.append("🟢 Resolved\n");
                    sb.append("   Admin: ").append(admin).append("\n");
                    sb.append("   ").append(DateUtils.formatIsoTimestamp(item.changed_at)).append("\n");
                    if (item.note != null && !item.note.trim().isEmpty()) {
                        sb.append("   Resolution: ").append(item.note).append("\n");
                    }
                    sb.append("\n");
                } else if ("in_progress".equals(newStatus) || "in-progress".equals(newStatus)) {
                    sb.append("🔵 In Progress\n");
                    sb.append("   Admin: ").append(admin).append("\n");
                    sb.append("   ").append(DateUtils.formatIsoTimestamp(item.changed_at)).append("\n\n");
                } else {
                    sb.append("⏳ ").append(displayStatus(item.new_status)).append("\n");
                    sb.append("   Admin: ").append(admin).append("\n");
                    sb.append("   ").append(DateUtils.formatIsoTimestamp(item.changed_at)).append("\n\n");
                }
            }
        } else {
            // Fallback timeline from current status fields if statusHistoryList is not populated
            if ("resolved".equalsIgnoreCase(currentStatus)) {
                String admin = (resolvedByAdminName != null && !resolvedByAdminName.isEmpty())
                        ? "Admin " + resolvedByAdminName : "Authority";
                sb.append("🟢 Resolved\n");
                sb.append("   Admin: ").append(admin).append("\n");
                sb.append("   ").append(DateUtils.formatIsoTimestamp(resolvedAt)).append("\n");
                if (resolutionNote != null && !resolutionNote.trim().isEmpty()) {
                    sb.append("   Resolution: ").append(resolutionNote).append("\n");
                }
            } else if ("in_progress".equalsIgnoreCase(currentStatus)) {
                String admin = (assignedAdminName != null && !assignedAdminName.isEmpty())
                        ? "Admin " + assignedAdminName : "Authority";
                sb.append("🔵 In Progress\n");
                sb.append("   Admin: ").append(admin).append("\n");
            } else {
                sb.append("⏳ Pending Authority Review\n");
            }
        }

        tvTimeline.setText(sb.toString().trim());
    }

    // ── AI Intelligence ───────────────────────────────────────────────────────

    private void fetchAIIntelligence() {
        if (llAiPanel == null) return;
        if (remoteReportId == null || remoteReportId.isEmpty()) {
            showAiUnavailable("No remote report ID — AI intelligence unavailable.");
            return;
        }

        showAiLoading(true);
        reportRepository.getAIIntelligence(remoteReportId,
                new ReportRepository.AIIntelligenceCallback() {
                    @Override
                    public void onSuccess(AIIntelligenceResponse r) {
                        runOnUiThread(() -> populateAIPanel(r));
                    }

                    @Override
                    public void onHttpError(int statusCode) {
                        runOnUiThread(() -> showAiUnavailable("AI analysis returned HTTP " + statusCode));
                    }

                    @Override
                    public void onFailure(Throwable throwable) {
                        String errorMsg = throwable.getMessage() != null
                                ? throwable.getMessage() : throwable.getClass().getSimpleName();
                        runOnUiThread(() -> showAiUnavailable("AI fetch error: " + errorMsg));
                    }

                    @Override
                    public void onConfigurationError(String message) {
                        runOnUiThread(() -> showAiUnavailable("Config: " + message));
                    }
                });
    }

    private void reRunAIAnalysis() {
        if (llAiPanel == null) return;
        if (remoteReportId == null || remoteReportId.isEmpty()) {
            showAiUnavailable("No remote report ID — AI analysis unavailable.");
            return;
        }

        showAiLoading(true);
        reportRepository.reRunAIAnalysis(remoteReportId,
                new ReportRepository.AIIntelligenceCallback() {
                    @Override
                    public void onSuccess(AIIntelligenceResponse r) {
                        runOnUiThread(() -> {
                            populateAIPanel(r);
                            Toast.makeText(AdminComplaintDetailActivity.this,
                                    "✅ AI Analysis refreshed", Toast.LENGTH_SHORT).show();
                        });
                    }

                    @Override
                    public void onHttpError(int statusCode) {
                        runOnUiThread(() -> showAiUnavailable("AI re-run returned HTTP " + statusCode));
                    }

                    @Override
                    public void onFailure(Throwable throwable) {
                        String errorMsg = throwable.getMessage() != null
                                ? throwable.getMessage() : throwable.getClass().getSimpleName();
                        runOnUiThread(() -> showAiUnavailable("AI re-run error: " + errorMsg));
                    }

                    @Override
                    public void onConfigurationError(String message) {
                        runOnUiThread(() -> showAiUnavailable("Config: " + message));
                    }
                });
    }

    private void populateAIPanel(AIIntelligenceResponse r) {
        showAiLoading(false);
        if (llAiPanel != null) llAiPanel.setVisibility(View.VISIBLE);

        if (r == null) {
            showAiUnavailable("No AI intelligence returned.");
            return;
        }

        if (!r.analysis_available) {
            showAiUnavailable("AI analysis pending. Tap '🔄 Re-run AI Analysis' to evaluate evidence.");
            return;
        }

        // 1. AI/VLM EVIDENCE
        String issue = (r.issue_category != null && !r.issue_category.isEmpty())
                ? r.issue_category : (category != null ? category : "Reported Issue");
        String summary = (r.text_analysis != null && r.text_analysis.summary != null && !r.text_analysis.summary.isEmpty())
                ? r.text_analysis.summary : (r.explanation != null ? r.explanation : "Summary unavailable");

        setText(tvAiSummary, "🔍 AI/VLM EVIDENCE\n───────────────────\n📋 Issue: " + issue + "\n📝 Summary: " + summary);

        if (r.text_analysis != null && r.text_analysis.available) {
            AIIntelligenceResponse.TextAnalysis ta = r.text_analysis;
            setText(tvAiKeywords, "🏷 Keywords: " + joinList(ta.keywords));

            String urgencyStr = (ta.urgency_indicators != null && !ta.urgency_indicators.isEmpty())
                    ? joinList(ta.urgency_indicators) : "UNKNOWN";
            setText(tvAiUrgency, "⚡ Urgency: " + urgencyStr);

            String hazardStr = (ta.hazard_indicators != null && !ta.hazard_indicators.isEmpty())
                    ? joinList(ta.hazard_indicators) : "NONE_DETECTED";
            setText(tvAiHazard, "☢ Hazards: " + hazardStr);

            float conf = ta.confidence > 0 ? ta.confidence : 0f;
            String confStr = conf > 0 ? String.format(Locale.US, "%.0f%%", conf * 100f) : "0% (Unavailable)";
            setText(tvAiConfidence, "🎯 AI Confidence: " + confStr + "  |  Needs Review: " + (r.overall_needs_review ? "YES ⚠" : "NO ✓"));
        } else {
            setText(tvAiKeywords, "🏷 Keywords: —");
            setText(tvAiUrgency, "⚡ Urgency: UNKNOWN");
            setText(tvAiHazard, "☢ Hazards: UNKNOWN");
            float imgConf = (r.image_analysis != null && r.image_analysis.available) ? r.image_analysis.confidence : 0f;
            String confStr = imgConf > 0 ? String.format(Locale.US, "%.0f%%", imgConf * 100f) : "0% (Unavailable)";
            setText(tvAiConfidence, "🎯 AI Confidence: " + confStr + "  |  Needs Review: " + (r.overall_needs_review ? "YES ⚠" : "NO ✓"));
        }

        // Image validation & Consistency
        if (r.image_analysis != null && r.image_analysis.available) {
            AIIntelligenceResponse.ImageAnalysis ia = r.image_analysis;
            String imgResult = ia.validation_result != null ? ia.validation_result : "UNCERTAIN";
            String imgEmoji = "YES".equalsIgnoreCase(imgResult) ? "✅ YES" : ("NO".equalsIgnoreCase(imgResult) ? "❌ NO" : "❓ UNCERTAIN");
            String imgConf = ia.confidence > 0 ? String.format(Locale.US, " (%.0f%% confidence)", ia.confidence * 100f) : "";
            setText(tvAiImageResult, "📷 Image Validation: " + imgEmoji + imgConf);
        } else {
            setText(tvAiImageResult, "📷 Image Validation: No image provided");
        }

        String consistency = (r.evidence_consistency != null && r.evidence_consistency.consistency_status != null)
                ? r.evidence_consistency.consistency_status
                : (r.evidence_consistency != null && Boolean.TRUE.equals(r.evidence_consistency.agreement) ? "CONSISTENT" : "UNCERTAIN");
        String consistencyEmoji = "CONSISTENT".equalsIgnoreCase(consistency) ? "✅ CONSISTENT"
                : ("INCONSISTENT".equalsIgnoreCase(consistency) ? "❌ INCONSISTENT" : "❓ UNCERTAIN");

        // Update header badges
        if (r.risk != null && tvRisk != null) {
            String emoji = "HIGH".equalsIgnoreCase(r.risk.risk_level) || "CRITICAL".equalsIgnoreCase(r.risk.risk_level)
                    ? "🔴" : ("MEDIUM".equalsIgnoreCase(r.risk.risk_level) ? "🟡" : "🟢");
            tvRisk.setText(emoji + " " + String.format(Locale.US, "%.0f Risk (%s)", r.risk.risk_score, r.risk.risk_level));
        }

        if (tvRepeat != null) {
            if (r.duplicate != null && r.duplicate.is_duplicate) {
                tvRepeat.setVisibility(View.VISIBLE);
                tvRepeat.setText("⚠ DUPLICATE DETECTED");
            } else if (r.recurrence != null && r.recurrence.is_recurring) {
                tvRepeat.setVisibility(View.VISIBLE);
                tvRepeat.setText("⚠ RECURRING ISSUE");
            } else {
                tvRepeat.setVisibility(View.GONE);
            }
        }

        StringBuilder intelBuilder = new StringBuilder();
        intelBuilder.append("🔬 Evidence Consistency: ").append(consistencyEmoji).append("\n\n");

        // 2. RISK ASSESSMENT
        if (r.risk != null) {
            intelBuilder.append("🎯 RISK ASSESSMENT\n");
            intelBuilder.append("───────────────\n");
            intelBuilder.append("• Risk Score: ").append(String.format(Locale.US, "%.1f / 100", r.risk.risk_score))
                    .append(" (").append(r.risk.risk_level).append(")\n");
            if (r.risk.risk_factors != null && !r.risk.risk_factors.isEmpty()) {
                intelBuilder.append("• Risk Factors:\n");
                for (String factor : r.risk.risk_factors) {
                    intelBuilder.append("   - ").append(factor).append("\n");
                }
            }
            intelBuilder.append("\n");
        }

        // 3. DISPATCH PRIORITY
        if (r.priority != null) {
            intelBuilder.append("⚡ DISPATCH PRIORITY\n");
            intelBuilder.append("─────────────────\n");
            intelBuilder.append("• Priority Level: ").append(r.priority).append("\n");
            if (r.priority_reasons != null && !r.priority_reasons.isEmpty()) {
                intelBuilder.append("• Priority Reasons:\n");
                for (String reason : r.priority_reasons) {
                    intelBuilder.append("   - ").append(reason).append("\n");
                }
            }

            // Explicit Risk vs Priority alignment explanation
            if (r.risk != null) {
                boolean priorityElevated = ("HIGH".equalsIgnoreCase(r.priority) || "CRITICAL".equalsIgnoreCase(r.priority))
                        && ("LOW".equalsIgnoreCase(r.risk.risk_level) || "MEDIUM".equalsIgnoreCase(r.risk.risk_level));
                if (priorityElevated) {
                    intelBuilder.append("💡 Operational Alignment:\n");
                    intelBuilder.append("   \"Priority is ").append(r.priority)
                            .append(" because operational severity and corroborating reports require immediate attention despite the aggregate risk score (")
                            .append(String.format(Locale.US, "%.1f/100", r.risk.risk_score))
                            .append(").\"\n");
                }
            }
            intelBuilder.append("\n");
        }

        // 4. DUPLICATE INCIDENT CORROBORATION
        intelBuilder.append("👥 DUPLICATE INCIDENT CORROBORATION\n");
        intelBuilder.append("──────────────────────────────────\n");
        if (r.duplicate != null && r.duplicate.is_duplicate) {
            intelBuilder.append("• Duplicate Detected: YES\n");
            intelBuilder.append("• Related Report: ").append(r.duplicate.duplicate_report_id != null ? r.duplicate.duplicate_report_id : "Unavailable").append("\n");
            String distStr = (r.duplicate.duplicate_distance != null && r.duplicate.duplicate_distance > 0)
                    ? String.format(Locale.US, "%.1f m", r.duplicate.duplicate_distance) : "Unavailable";
            intelBuilder.append("• Distance: ").append(distStr).append("\n");
            String timeStr = (r.duplicate.duplicate_time_difference != null)
                    ? String.format(Locale.US, "%.1f hrs", r.duplicate.duplicate_time_difference) : "Unavailable";
            intelBuilder.append("• Time Difference: ").append(timeStr).append("\n");
            intelBuilder.append("• Reason: ").append(r.duplicate.duplicate_reason != null ? r.duplicate.duplicate_reason : "Corroborated by nearby incident report").append("\n");
        } else {
            intelBuilder.append("• Duplicate Detected: NO (Unique incident)\n");
        }
        intelBuilder.append("\n");

        // 5. SPATIAL & CLUSTERING
        if (r.spatial != null && r.spatial.is_hotspot) {
            intelBuilder.append("📍 HOTSPOT CLUSTERING\n");
            intelBuilder.append("────────────────────\n");
            intelBuilder.append("• Active Hotspot: YES (").append(r.spatial.cluster_size != null ? r.spatial.cluster_size : 0).append(" reports in cluster)\n\n");
        }

        // 6. AUTHORITY RECOMMENDATION
        if (r.recommendation != null && r.recommendation.is_available) {
            intelBuilder.append("🛡 AUTHORITY RECOMMENDATION\n");
            intelBuilder.append("─────────────────────────\n");
            intelBuilder.append("• Recommended Action: ").append(r.recommendation.recommended_action).append("\n");
            intelBuilder.append("• Operational Reason: ").append(r.recommendation.reason).append("\n");
        }

        setText(tvAiExplanation, intelBuilder.toString().trim());
    }

    private void showAiLoading(boolean loading) {
        if (pbAiLoading != null) pbAiLoading.setVisibility(loading ? View.VISIBLE : View.GONE);
        if (loading && llAiPanel != null) llAiPanel.setVisibility(View.GONE);
    }

    private void showAiUnavailable(String msg) {
        showAiLoading(false);
        if (llAiPanel != null) llAiPanel.setVisibility(View.VISIBLE);
        setText(tvAiSummary, "ℹ " + msg);
        setText(tvAiKeywords, "");
        setText(tvAiUrgency, "");
        setText(tvAiHazard, "");
        setText(tvAiConfidence, "");
        setText(tvAiImageResult, "");
        setText(tvAiExplanation, "");
    }

    private String joinList(List<String> list) {
        if (list == null || list.isEmpty()) return "—";
        return android.text.TextUtils.join(", ", list);
    }

    // ── Buttons ───────────────────────────────────────────────────────────────

    private void setupButtons() {
        if (btnUpdateStatus != null) btnUpdateStatus.setOnClickListener(v -> showStatusDialog());
        if (btnUploadAfter  != null) btnUploadAfter.setOnClickListener(v -> openCamera());
        if (btnFetchAI      != null) btnFetchAI.setOnClickListener(v -> reRunAIAnalysis());
        if (btnResolveReport!= null) btnResolveReport.setOnClickListener(v -> resolveReport());

        if (btnMap != null) {
            boolean hasLocation = latitude != 0 || longitude != 0;
            btnMap.setEnabled(hasLocation);
            btnMap.setOnClickListener(v -> {
                Intent i = new Intent(this, MapsActivity.class);
                i.putExtra("LAT",   latitude);
                i.putExtra("LNG",   longitude);
                i.putExtra("TITLE", category != null ? category : "Report");
                startActivity(i);
            });
        }
    }

    // ── Status update ─────────────────────────────────────────────────────────

    private void showStatusDialog() {
        if ("resolved".equalsIgnoreCase(currentStatus)) {
            Toast.makeText(this, "Report is already resolved.", Toast.LENGTH_SHORT).show();
            return;
        }

        String[] options = {"Pending", "In Progress", "Resolved"};
        new AlertDialog.Builder(this)
                .setTitle("Update Status")
                .setItems(options, (d, which) -> updateStatus(options[which]))
                .setNegativeButton("Cancel", null)
                .show();
    }

    private void updateStatus(String newStatus) {
        if (statusUpdating) return;
        statusUpdating = true;
        if (btnUpdateStatus != null) {
            btnUpdateStatus.setEnabled(false);
            btnUpdateStatus.setText("Updating…");
        }

        if (remoteReportId == null || remoteReportId.isEmpty()) {
            applyLocalStatusOnly(newStatus);
            finishStatusUpdate("No remote ID — status saved locally only.");
            return;
        }

        reportRepository.updateReportStatus(remoteReportId, toRemoteStatus(newStatus),
                new ReportRepository.StatusUpdateCallback() {
                    @Override
                    public void onSuccess(RemoteReportResponse response) {
                        currentStatus = response.status;
                        if (response.assigned_admin_name != null) assignedAdminName = response.assigned_admin_name;
                        if (response.resolved_by_admin_name != null) resolvedByAdminName = response.resolved_by_admin_name;
                        if (response.resolved_at != null) resolvedAt = response.resolved_at;
                        if (response.status_history != null) statusHistoryList = response.status_history;

                        applyLocalStatusOnly(newStatus);
                        updateResolutionUI();
                        populateTimeline();
                        finishStatusUpdate("✅ Status updated on server: " + newStatus);
                    }

                    @Override
                    public void onHttpError(int statusCode) {
                        applyLocalStatusOnly(newStatus);
                        finishStatusUpdate("Server HTTP " + statusCode + ". Saved locally.");
                    }

                    @Override
                    public void onConnectionFailure(Throwable throwable) {
                        applyLocalStatusOnly(newStatus);
                        finishStatusUpdate("Server unreachable. Saved locally.");
                    }

                    @Override
                    public void onConfigurationError(String message) {
                        applyLocalStatusOnly(newStatus);
                        finishStatusUpdate("Config error. Saved locally.");
                    }
                });
    }

    private void applyLocalStatusOnly(String newStatus) {
        currentStatus = newStatus;
        if (localComplaint != null) {
            com.example.smartcivicapp.database.ComplaintDao dao =
                    com.example.smartcivicapp.database.AppDatabase.getInstance(this).complaintDao();
            dao.updateStatus(localComplaint.id, newStatus);
            String updated = com.example.smartcivicapp.utils.TimelineHelper.appendEvent(
                    localComplaint.timelineJson, newStatus);
            dao.updateTimeline(localComplaint.id, updated);
            if ("Resolved".equalsIgnoreCase(newStatus)) {
                dao.setResolvedAt(localComplaint.id, System.currentTimeMillis());
            }
            localComplaint.status = newStatus;
            localComplaint.timelineJson = updated;
            NotificationHelper.showStatusUpdateNotification(
                    this, localComplaint.id, category != null ? category : "Issue", newStatus);
        }
        runOnUiThread(() -> {
            if (tvStatus != null) {
                tvStatus.setText(displayStatus(newStatus));
                applyStatusChipColor(tvStatus, newStatus);
            }
        });
    }

    private void finishStatusUpdate(String message) {
        runOnUiThread(() -> {
            statusUpdating = false;
            if (btnUpdateStatus != null) {
                if ("resolved".equalsIgnoreCase(currentStatus)) {
                    btnUpdateStatus.setEnabled(false);
                    btnUpdateStatus.setText("Status: Resolved ✓");
                } else {
                    btnUpdateStatus.setEnabled(true);
                    btnUpdateStatus.setText("Update Status");
                }
            }
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
        });
    }

    private String toRemoteStatus(String status) {
        return "In Progress".equals(status) ? "in_progress" : status.toLowerCase(Locale.US);
    }

    // ── Resolve Report ────────────────────────────────────────────────────────

    private void resolveReport() {
        if (statusUpdating) return;

        String note = etResolutionNote != null && etResolutionNote.getText() != null
                ? etResolutionNote.getText().toString().trim() : "";

        if (remoteReportId == null || remoteReportId.isEmpty()) {
            Toast.makeText(this, "Cannot resolve local-only report remotely.", Toast.LENGTH_SHORT).show();
            return;
        }

        statusUpdating = true;
        if (btnResolveReport != null) {
            btnResolveReport.setEnabled(false);
            btnResolveReport.setText("Resolving…");
        }

        reportRepository.resolveReport(remoteReportId, note, currentAfterImageFile,
                new ReportRepository.StatusUpdateCallback() {
                    @Override
                    public void onSuccess(RemoteReportResponse response) {
                        currentStatus = response.status;
                        resolutionNote = response.resolution_note != null ? response.resolution_note : note;
                        resolvedAt = response.resolved_at;
                        resolvedByAdminName = response.resolved_by_admin_name;
                        if (response.resolution_image_path != null) {
                            resolutionImagePath = response.resolution_image_path;
                        }
                        if (response.status_history != null) {
                            statusHistoryList = response.status_history;
                        }

                        applyLocalStatusOnly("Resolved");
                        currentAfterImageFile = null;
                        runOnUiThread(() -> {
                            updateResolutionUI();
                            populateAfterImage();
                            populateTimeline();
                            finishResolve("Resolution saved successfully ✅");
                        });
                    }

                    @Override
                    public void onHttpError(int statusCode) {
                        finishResolve("Resolution image upload failed (HTTP " + statusCode + "). Report was NOT marked resolved.");
                    }

                    @Override
                    public void onConnectionFailure(Throwable throwable) {
                        finishResolve("Resolution image upload failed (Network Error). Report was NOT marked resolved.");
                    }

                    @Override
                    public void onConfigurationError(String message) {
                        finishResolve("Config Error: " + message);
                    }
                });
    }

    private void finishResolve(String message) {
        runOnUiThread(() -> {
            statusUpdating = false;
            if (btnResolveReport != null) {
                btnResolveReport.setEnabled(true);
                btnResolveReport.setText("✅ Resolve Report");
            }
            Toast.makeText(this, message, Toast.LENGTH_SHORT).show();
        });
    }

    // ── Camera / After image ──────────────────────────────────────────────────

    private void openCamera() {
        if ("resolved".equalsIgnoreCase(currentStatus)) {
            Toast.makeText(this, "Report is already resolved.", Toast.LENGTH_SHORT).show();
            return;
        }
        Intent i = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        if (i.resolveActivity(getPackageManager()) != null) cameraLauncher.launch(i);
    }

    private void saveAfterImage(Bitmap bmp) {
        try {
            String name = "after_" + (remoteReportId != null
                    ? remoteReportId.replace("-", "") : "local") + ".jpg";
            File file = new File(getFilesDir(), name);
            FileOutputStream out = new FileOutputStream(file);
            bmp.compress(Bitmap.CompressFormat.JPEG, 80, out);
            out.close();
            currentAfterImageFile = file;
            if (ivAfter != null) {
                ivAfter.setVisibility(View.VISIBLE);
                ivAfter.setImageBitmap(bmp);
            }
            if (tvAfterUnavailable != null) tvAfterUnavailable.setVisibility(View.GONE);
            Toast.makeText(this, "After-image selected. It will be uploaded when you resolve the report.", Toast.LENGTH_LONG).show();

            // Persist to Room if local complaint available
            if (localComplaint != null) {
                com.example.smartcivicapp.database.AppDatabase.getInstance(this)
                        .complaintDao().updateAfterImage(localComplaint.id, file.getAbsolutePath());
            }
        } catch (IOException e) {
            Toast.makeText(this, "Failed to save image", Toast.LENGTH_SHORT).show();
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private void setText(TextView tv, String text) {
        if (tv != null) tv.setText(text != null ? text : "");
    }

    private String displayStatus(String raw) {
        if (raw == null) return "Unknown";
        switch (raw.toLowerCase(Locale.US)) {
            case "pending":     return "Pending";
            case "in_progress":
            case "in-progress": return "In Progress";
            case "resolved":    return "Resolved";
            default:            return raw;
        }
    }
}
