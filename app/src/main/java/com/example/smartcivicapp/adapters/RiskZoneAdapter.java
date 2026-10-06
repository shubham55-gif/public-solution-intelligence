package com.example.smartcivicapp.adapters;

import android.content.Context;
import android.graphics.Color;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.example.smartcivicapp.R;
import com.example.smartcivicapp.database.WardCount;

import java.util.List;

/**
 * RiskZoneAdapter — displays ward risk analysis in RiskZonesActivity.
 */
public class RiskZoneAdapter extends RecyclerView.Adapter<RiskZoneAdapter.ViewHolder> {

    private final Context        context;
    private final List<WardCount> list;

    public RiskZoneAdapter(Context context, List<WardCount> list) {
        this.context = context;
        this.list    = list;
    }

    @NonNull
    @Override
    public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View v = LayoutInflater.from(context)
                .inflate(R.layout.item_risk_zone, parent, false);
        return new ViewHolder(v);
    }

    @Override
    public void onBindViewHolder(@NonNull ViewHolder h, int pos) {
        WardCount wc = list.get(pos);

        h.tvWardName.setText(wc.ward != null ? wc.ward : "Unknown Area");
        h.tvCount.setText(wc.cnt + " complaint" + (wc.cnt != 1 ? "s" : ""));

        // Determine risk level
        String level;
        int    dotColor;
        int    textColor;
        int    bgRes;

        if (wc.cnt >= 3) {
            level     = "HIGH";
            dotColor  = Color.parseColor("#C62828");
            textColor = Color.parseColor("#C62828");
            bgRes     = R.drawable.bg_risk_high;
        } else if (wc.cnt == 2) {
            level     = "MEDIUM";
            dotColor  = Color.parseColor("#F57C00");
            textColor = Color.parseColor("#F57C00");
            bgRes     = R.drawable.bg_status_pending;
        } else {
            level     = "LOW";
            dotColor  = Color.parseColor("#388E3C");
            textColor = Color.parseColor("#388E3C");
            bgRes     = R.drawable.bg_status_resolved;
        }

        h.tvRiskLevel.setText(level);
        h.tvRiskLevel.setTextColor(textColor);
        h.tvRiskLevel.setBackgroundResource(bgRes);
        h.viewDot.setBackgroundTintList(
                android.content.res.ColorStateList.valueOf(dotColor));
    }

    @Override
    public int getItemCount() { return list != null ? list.size() : 0; }

    static class ViewHolder extends RecyclerView.ViewHolder {
        TextView tvWardName, tvCount, tvRiskLevel;
        View     viewDot;

        ViewHolder(@NonNull View v) {
            super(v);
            tvWardName  = v.findViewById(R.id.tvWardName);
            tvCount     = v.findViewById(R.id.tvComplaintCount);
            tvRiskLevel = v.findViewById(R.id.tvRiskLevel);
            viewDot     = v.findViewById(R.id.viewRiskDot);
        }
    }
}
