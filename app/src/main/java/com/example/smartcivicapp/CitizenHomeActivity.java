package com.example.smartcivicapp;

import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;
import androidx.cardview.widget.CardView;

import com.example.smartcivicapp.network.models.UserProfileResponse;
import com.example.smartcivicapp.repositories.AuthRepository;

/**
 * CitizenHomeActivity — modern citizen dashboard with live stats cards.
 *
 * Source of truth: GET /api/v1/auth/profile
 * Refreshes live statistics (Total, Pending, Resolved) on onResume().
 */
public class CitizenHomeActivity extends AppCompatActivity {

    private static final String TAG = "CitizenHomeActivity";

    private PrefManager pref;
    private AuthRepository authRepository;
    private boolean isStatsLoading = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        pref = new PrefManager(this);
        if (!pref.isCitizenLoggedIn()) {
            startActivity(new Intent(this, CitizenLoginActivity.class));
            finish();
            return;
        }

        setContentView(R.layout.activity_citizen_home);

        authRepository = new AuthRepository(this);

        setupWelcomeCard();
        setupNavButtons();
        loadProfileStatistics();
    }

    @Override
    protected void onResume() {
        super.onResume();
        // Refresh live stats each time user returns to dashboard
        loadProfileStatistics();
    }

    private void setupWelcomeCard() {
        TextView tvWelcomeName = findViewById(R.id.tvWelcomeName);
        if (tvWelcomeName != null) {
            tvWelcomeName.setText("Welcome back,\n" + pref.getCitizenName());
        }
        TextView tvWelcomeSub = findViewById(R.id.tvWelcomeSub);
        if (tvWelcomeSub != null) {
            tvWelcomeSub.setText("Together, we can improve our community.");
        }
    }

    private void loadProfileStatistics() {
        if (isStatsLoading) return;
        isStatsLoading = true;

        Log.d(TAG, "Fetching live citizen statistics from /api/v1/auth/profile...");

        authRepository.getProfile(new AuthRepository.ProfileCallback() {
            @Override
            public void onSuccess(UserProfileResponse profile) {
                isStatsLoading = false;
                if (profile == null) return;

                Log.d(TAG, String.format("Live stats received -> Total: %d, Pending: %d, InProgress: %d, Resolved: %d",
                        profile.totalReports, profile.pendingReports, profile.inProgressReports, profile.resolvedReports));

                runOnUiThread(() -> {
                    TextView tvTotal    = findViewById(R.id.tvStatTotal);
                    TextView tvPending  = findViewById(R.id.tvStatPending);
                    TextView tvResolved = findViewById(R.id.tvStatResolved);

                    if (tvTotal != null) {
                        tvTotal.setText(String.valueOf(profile.totalReports));
                    }
                    if (tvPending != null) {
                        tvPending.setText(String.valueOf(profile.pendingReports));
                    }
                    if (tvResolved != null) {
                        tvResolved.setText(String.valueOf(profile.resolvedReports));
                    }

                    if (profile.name != null && !profile.name.trim().isEmpty()) {
                        TextView tvWelcomeName = findViewById(R.id.tvWelcomeName);
                        if (tvWelcomeName != null) {
                            tvWelcomeName.setText("Hello, " + profile.name + " 👋");
                        }
                    }
                });
            }

            @Override
            public void onError(String message, int statusCode) {
                isStatsLoading = false;
                Log.w(TAG, "Failed to load live profile statistics: HTTP " + statusCode + " - " + message);
                // Keep last known values visible, do not overwrite with 0
            }

            @Override
            public void onFailure(Throwable throwable) {
                isStatsLoading = false;
                Log.w(TAG, "Network error while loading live profile statistics: " + throwable.getMessage());
                // Keep last known values visible, do not overwrite with 0
            }
        });
    }

    private void setupNavButtons() {
        // Quick Report button (prominent)
        Button btnReport = findViewById(R.id.btnReportIssue);
        if (btnReport != null) {
            btnReport.setOnClickListener(v ->
                    startActivity(new Intent(this, ReportIssueActivity.class)));
        }

        // My Complaints
        CardView cardComplaints = findViewById(R.id.cardMyComplaints);
        if (cardComplaints != null) {
            cardComplaints.setOnClickListener(v ->
                    startActivity(new Intent(this, ComplaintListActivity.class)));
        }

        // Map
        CardView cardMap = findViewById(R.id.cardMap);
        if (cardMap != null) {
            cardMap.setOnClickListener(v ->
                    startActivity(new Intent(this, MapsActivity.class)));
        }

        // Updates / Notifications
        CardView cardNotifications = findViewById(R.id.cardNotifications);
        if (cardNotifications != null) {
            cardNotifications.setOnClickListener(v ->
                    startActivity(new Intent(this, ComplaintListActivity.class)));
        }

        // Logout
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
}
