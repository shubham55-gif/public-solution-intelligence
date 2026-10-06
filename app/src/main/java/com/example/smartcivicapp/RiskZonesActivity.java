package com.example.smartcivicapp;

import android.os.Bundle;
import android.view.View;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.smartcivicapp.adapters.RiskZoneAdapter;
import com.example.smartcivicapp.database.AppDatabase;
import com.example.smartcivicapp.database.WardCount;

import java.util.List;

/**
 * RiskZonesActivity — displays area risk analysis to admin.
 *
 * Shows each ward with:
 *  - Complaint count
 *  - Risk level (Low / Medium / High)
 *  - Repeat complaint flag
 *  - Decision support message
 */
public class RiskZonesActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_risk_zones);

        List<WardCount> wards = AppDatabase.getInstance(this)
                .complaintDao().getWardAnalysis();

        RecyclerView rv = findViewById(R.id.rvRiskZones);
        TextView tvEmpty = findViewById(R.id.tvEmpty);
        TextView tvDecision = findViewById(R.id.tvDecision);

        rv.setLayoutManager(new LinearLayoutManager(this));

        if (wards.isEmpty()) {
            rv.setVisibility(View.GONE);
            if (tvEmpty != null) tvEmpty.setVisibility(View.VISIBLE);
        } else {
            rv.setVisibility(View.VISIBLE);
            if (tvEmpty != null) tvEmpty.setVisibility(View.GONE);
            rv.setAdapter(new RiskZoneAdapter(this, wards));
        }

        if (tvDecision != null) {
            tvDecision.setText(buildDecisionText(wards));
        }
    }

    private String buildDecisionText(List<WardCount> wards) {
        if (wards.isEmpty()) return "No area data available yet.";

        StringBuilder sb = new StringBuilder("💡 RECOMMENDATIONS\n\n");
        for (WardCount wc : wards) {
            if (wc.cnt >= 3) {
                sb.append("• Deploy immediate resources to ").append(wc.ward)
                  .append(" — ").append(wc.cnt).append(" active complaints.\n");
            } else if (wc.cnt == 2) {
                sb.append("• Monitor ").append(wc.ward)
                  .append(" closely — ").append(wc.cnt).append(" complaints reported.\n");
            }
        }
        return sb.length() > 20 ? sb.toString() : "All areas are within normal range.";
    }
}
