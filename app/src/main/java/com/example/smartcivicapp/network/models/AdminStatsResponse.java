package com.example.smartcivicapp.network.models;

import com.google.gson.annotations.SerializedName;

public class AdminStatsResponse {
    @SerializedName("total_citizens")
    public int totalCitizens;

    @SerializedName("total_admins")
    public int totalAdmins;

    @SerializedName("total_reports")
    public int totalReports;

    @SerializedName("pending")
    public int pending;

    @SerializedName("in_progress")
    public int inProgress;

    @SerializedName("resolved")
    public int resolved;

    @SerializedName("high_risk")
    public int highRisk;

    @SerializedName("repeated")
    public int repeated;
}
