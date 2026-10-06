package com.example.smartcivicapp;

import android.os.Bundle;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.smartcivicapp.adapters.ComplaintAdapter;
import com.example.smartcivicapp.database.AppDatabase;
import com.example.smartcivicapp.database.ComplaintDao;
import com.example.smartcivicapp.entities.Complaint;
import com.example.smartcivicapp.network.models.RemoteReportMapper;
import com.example.smartcivicapp.network.models.RemoteReportResponse;
import com.example.smartcivicapp.repositories.ReportRepository;

import java.util.ArrayList;
import java.util.List;

/**
 * ComplaintListActivity — filterable complaint list.
 *
 * FEATURES:
 *  - Status filter spinner (All / Pending / In Progress / Resolved)
 *  - Issue type filter spinner
 *  - Empty state message
 *  - Complaint count header
 *
 * Admin path: fetches ALL reports from FastAPI so every row carries a real
 * remoteReportId (PostgreSQL UUID). Falls back to Room if network is unavailable.
 * Citizen path: fetches own reports from FastAPI (existing behaviour).
 */
public class ComplaintListActivity extends AppCompatActivity {

    private RecyclerView recyclerView;
    private TextView     tvEmpty, tvCount;
    private Spinner      spinnerStatus, spinnerType;
    private ComplaintDao dao;
    private ReportRepository reportRepository;
    private PrefManager pref;

    private List<Complaint> remoteComplaints;
    private boolean remoteLoadInProgress;
    private boolean remoteLoadFinished;

    private String currentStatus = "All";
    private String currentType   = "All";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_complaint_list);

        dao              = AppDatabase.getInstance(this).complaintDao();
        reportRepository = new ReportRepository(this);
        pref             = new PrefManager(this);
        recyclerView     = findViewById(R.id.recyclerView);
        tvEmpty          = findViewById(R.id.tvEmpty);
        tvCount          = findViewById(R.id.tvCount);
        spinnerStatus    = findViewById(R.id.spinnerStatus);
        spinnerType      = findViewById(R.id.spinnerType);

        recyclerView.setLayoutManager(new LinearLayoutManager(this));

        setupFilters();

        if (pref.isAdmin()) {
            // Admin: always fetch from FastAPI — every Complaint row gets a real
            // remoteReportId (PostgreSQL UUID) so detail/AI/resolve all work.
            loadAdminRemoteComplaints();
        } else if (pref.isCitizen()) {
            loadRemoteComplaints();
        } else {
            renderComplaints();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (pref.isAdmin()) {
            remoteLoadInProgress = false;
            remoteLoadFinished = false;
            loadAdminRemoteComplaints();
        } else if (pref.isCitizen()) {
            remoteLoadInProgress = false;
            remoteLoadFinished = false;
            loadRemoteComplaints();
        }
    }

    // ── Filters ────────────────────────────────────────────────────────────────

    private void setupFilters() {
        String[] statuses = {"All", "Pending", "In Progress", "Resolved"};
        spinnerStatus.setAdapter(new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item, statuses));
        spinnerStatus.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> p, View v, int pos, long id) {
                currentStatus = statuses[pos];
                renderComplaints();
            }
            @Override public void onNothingSelected(AdapterView<?> p) {}
        });

        String[] types = {"All", "Road Damage", "Garbage Overflow",
                "Water Leakage", "Street Light Issue"};
        spinnerType.setAdapter(new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_item, types));
        spinnerType.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> p, View v, int pos, long id) {
                currentType = types[pos];
                renderComplaints();
            }
            @Override public void onNothingSelected(AdapterView<?> p) {}
        });
    }

    // ── Admin: fetch all reports from FastAPI ──────────────────────────────────

    /**
     * Fetches every report from the backend (authority view).
     * Each returned Complaint carries its PostgreSQL UUID as remoteReportId so
     * AdminComplaintDetailActivity can perform AI fetch, status update, resolve, etc.
     */
    private void loadAdminRemoteComplaints() {
        if (remoteLoadInProgress || remoteLoadFinished) return;
        remoteLoadInProgress = true;
        showLoadingMessage("Loading reports from server…");

        reportRepository.getAllReports(new ReportRepository.AdminReportListCallback() {
            @Override
            public void onSuccess(List<RemoteReportResponse> reports, int total) {
                List<Complaint> complaints = new ArrayList<>(reports.size());
                for (RemoteReportResponse r : reports) {
                    try {
                        complaints.add(RemoteReportMapper.toComplaint(r));
                    } catch (Exception ignored) {
                        // Skip any individual malformed entry; keep rest.
                    }
                }
                runOnUiThread(() -> {
                    remoteLoadInProgress = false;
                    remoteLoadFinished   = true;
                    remoteComplaints     = complaints;
                    renderComplaints();
                });
            }

            @Override
            public void onHttpError(int statusCode) {
                showAdminFallback("Server returned HTTP " + statusCode + ". Showing local data.");
            }

            @Override
            public void onFailure(Throwable throwable) {
                showAdminFallback("Cannot reach FastAPI. Showing local cached data.");
            }

            @Override
            public void onConfigurationError(String message) {
                showAdminFallback("Config error: " + message + ". Showing local data.");
            }
        });
    }

    private void showAdminFallback(String message) {
        runOnUiThread(() -> {
            remoteLoadInProgress = false;
            remoteLoadFinished   = true;
            remoteComplaints     = null; // Falls through to Room in renderComplaints()
            Toast.makeText(this, message, Toast.LENGTH_LONG).show();
            renderComplaints();
        });
    }

    // ── Citizen: fetch own reports from FastAPI ────────────────────────────────

    private void loadRemoteComplaints() {
        if (remoteLoadInProgress || remoteLoadFinished) return;
        remoteLoadInProgress = true;
        showLoadingMessage("Loading complaints…");

        reportRepository.getMyReports(new ReportRepository.ReportListCallback() {
            @Override
            public void onSuccess(List<Complaint> reports) {
                runOnUiThread(() -> {
                    remoteLoadInProgress = false;
                    remoteLoadFinished   = true;
                    remoteComplaints     = reports;
                    renderComplaints();
                });
            }

            @Override
            public void onHttpError(int statusCode) {
                showRemoteFallback("Could not load complaints (HTTP " + statusCode + ").");
            }

            @Override
            public void onFailure(Throwable throwable) {
                showRemoteFallback("Could not reach the server. Showing saved complaints.");
            }

            @Override
            public void onMalformedResponse(Throwable throwable) {
                showRemoteFallback("Server returned invalid data. Showing saved complaints.");
            }

            @Override
            public void onConfigurationError(String message) {
                showRemoteFallback("Server not configured. Showing saved complaints.");
            }
        });
    }

    private void showRemoteFallback(String message) {
        runOnUiThread(() -> {
            remoteLoadInProgress = false;
            remoteLoadFinished   = true;
            remoteComplaints     = null;
            Toast.makeText(this, message, Toast.LENGTH_LONG).show();
            renderComplaints();
        });
    }

    // ── Render ────────────────────────────────────────────────────────────────

    private void showLoadingMessage(String message) {
        if (tvEmpty != null) {
            tvEmpty.setText(message);
            tvEmpty.setVisibility(View.VISIBLE);
        }
        recyclerView.setVisibility(View.GONE);
    }

    private void renderComplaints() {
        List<Complaint> list;

        boolean allStatus = "All".equals(currentStatus);
        boolean allType   = "All".equals(currentType);

        if (remoteComplaints != null) {
            list = new ArrayList<>();
            for (Complaint c : remoteComplaints) {
                if ((!allStatus && !currentStatus.equals(c.status))
                        || (!allType && !currentType.equals(c.issueType))) {
                    continue;
                }
                list.add(c);
            }
        } else if (allStatus && allType) {
            list = dao.getAllComplaints();
        } else if (!allStatus && allType) {
            list = dao.getComplaintsByStatus(currentStatus);
        } else if (allStatus) {
            list = dao.getComplaintsByIssueType(currentType);
        } else {
            list = dao.getComplaintsByStatusAndType(currentStatus, currentType);
        }

        if (tvCount != null) {
            tvCount.setText(list.size() + " complaint" + (list.size() != 1 ? "s" : ""));
        }

        if (list.isEmpty()) {
            recyclerView.setVisibility(View.GONE);
            if (tvEmpty != null) {
                tvEmpty.setText("No complaints found");
                tvEmpty.setVisibility(View.VISIBLE);
            }
        } else {
            recyclerView.setVisibility(View.VISIBLE);
            if (tvEmpty != null) tvEmpty.setVisibility(View.GONE);
            recyclerView.setAdapter(new ComplaintAdapter(this, list));
        }
    }
}
